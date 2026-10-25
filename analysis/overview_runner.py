"""저장 분석 결과만 읽는 공용 overview 생성기. 배포 파일은 덮어쓰지 않는다."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from typing import Literal

from openai import OpenAI
from .llm import configured_settings
from .overview_contract import Advice, Category, Overview, StrictModel
from .overview_generation import finalize, make_input
from .overview_prompt import OVERVIEW_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[1]


class SummaryPart(StrictModel):
    audience: Literal['instructor', 'learner']
    left: list[Advice]
    right: list[Advice]
    suggestion: str | None


class CategoryPart(StrictModel):
    categories: list[Category]


class OverviewTruncated(ValueError):
    """출력 토큰 제한에 도달한 경우만 분할 호출한다."""


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def strict_schema(model):
    schema = deepcopy(model.model_json_schema())
    def visit(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if 'properties' in node:
                node['additionalProperties'] = False
                node['required'] = list(node['properties'])
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(schema)
    return {'type': 'json_schema', 'name': model.__name__, 'strict': True, 'schema': schema}


def request_part(client, payload, schema, instruction, model, effort, calls, audit_path):
    call = {'part': instruction, 'status': 'requesting'}
    calls.append(call)
    save(audit_path, calls)
    settings = {'reasoning': {'effort': effort}}
    if effort == 'none':
        settings['temperature'] = 0
    try:
        # 완료 상태를 먼저 확인해 SDK 자동 파서에 잘린 JSON을 넘기지 않는다.
        response = client.responses.create(model=model, store=False,
            instructions=OVERVIEW_INSTRUCTIONS + '\n[이번 출력 범위]\n' + instruction,
            input=json.dumps(payload, ensure_ascii=False), text={'format': strict_schema(schema)},
            max_output_tokens=18000 if schema is Overview else 8000, **settings)
        call.update(status=response.status, model=response.model,
                    usage=response.usage.model_dump() if response.usage else None,
                    output_text=response.output_text)
        reason = getattr(response.incomplete_details, 'reason', None)
        call['incomplete_reason'] = reason
        save(audit_path, calls)
        if response.status == 'incomplete' and reason == 'max_output_tokens':
            raise OverviewTruncated('Overview reached the output token limit')
        if response.status != 'completed' or not response.output_text:
            raise ValueError('Overview did not complete')
        return schema.model_validate_json(response.output_text).model_dump()
    except Exception as error:
        if call['status'] == 'requesting':
            call['status'] = 'failed'
        call['error_type'] = type(error).__name__
        save(audit_path, calls)
        raise


def generate(path, out, audit):
    path, out, audit = Path(path), Path(out), Path(audit)
    validate_directories(path.parent, out, audit)
    source_bytes = path.read_bytes()
    source = json.loads(source_bytes)
    if source['meta']['failed'] or source['meta']['model'] == 'mock':
        raise ValueError('Only successful real-model source files are accepted')
    audience = 'learner' if path.stem.endswith('_all') else 'instructor'
    payload = make_input(source, audience)
    key, model, effort = configured_settings()
    calls = []
    audit_path = audit / f'{path.stem}.calls.json'
    started = time.perf_counter()
    split = False
    with OpenAI(api_key=key, timeout=180, max_retries=0) as client:
        def request(data, schema, instruction):
            return request_part(client, data, schema, instruction, model, effort, calls, audit_path)
        try:
            raw = request(payload, Overview, '전체 overview를 출력한다.')
        except OverviewTruncated:
            split = True
            raw = request(payload, SummaryPart,
                          'audience, left, right, suggestion만 출력한다. categories는 출력하지 않는다.')
            raw['categories'] = []
            codes = sorted({i['category'] for r in payload['reviews'] for i in r['items']})
            # 한 항목도 잘리면 중단한다. 무제한 재시도나 부분 결과 저장을 하지 않는다.
            for code in codes:
                part = deepcopy(payload)
                part['summary_by_category'] = [r for r in part['summary_by_category'] if r['category'] == code]
                for review in part['reviews']:
                    review['items'] = [i for i in review['items'] if i['category'] == code]
                part['reviews'] = [r for r in part['reviews'] if r['items']]
                value = request(part, CategoryPart, f'categories만 출력한다. 항목 {code} 하나만 정확히 한 번 출력한다.')
                if [c['category'] for c in value['categories']] != [code]:
                    raise ValueError('Split category response has a missing or extra category')
                raw['categories'].extend(value['categories'])
    save(audit / f'{path.stem}.raw.json', raw)
    overview, findings = finalize(raw, source, audience)
    result = {**source, 'overview': overview}
    assert {k: v for k, v in result.items() if k != 'overview'} == {k: v for k, v in source.items() if k != 'overview'}
    if path.read_bytes() != source_bytes:
        raise ValueError('Source changed during generation')
    record = {'file': path.name, 'audience': audience,
              'status': 'generated_needs_review' if findings else 'generated',
              'source_sha256': hashlib.sha256(source_bytes).hexdigest(), 'model': model,
              'prompt_sha256': hashlib.sha256(OVERVIEW_INSTRUCTIONS.encode()).hexdigest(),
              'split_fallback': split, 'overview_calls_attempted': len(calls),
              'latency_ms': round((time.perf_counter() - started) * 1000), 'findings': findings}
    save(audit / f'{path.stem}.generation.json', record)
    save(out / path.name, result)
    return record


def validate_directories(input_dir, out_dir, audit_dir, workers=2):
    source, out, audit = map(lambda p: Path(p).resolve(), (input_dir, out_dir, audit_dir))
    if workers not in (1, 2, 3):
        raise ValueError('workers must be 1, 2 or 3')
    for a, b in ((source, out), (source, audit), (out, audit)):
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('Input, staging output and audit directories must be separate')
    return source, out, audit


def run_batch(input_dir, out_dir, audit_dir, workers=2):
    source, out, audit = validate_directories(input_dir, out_dir, audit_dir, workers)
    semester, merged = sorted(source.glob('*_202*.json')), sorted(source.glob('*_all.json'))
    if len(semester) != 8 or len(merged) != 4:
        raise ValueError('Expected 8 semester files and 4 merged course files')
    records = []
    for batch in (semester, merged):
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = {pool.submit(generate, path, out, audit): path for path in batch}
            for job in as_completed(jobs):
                path = jobs[job]
                try:
                    record = job.result()
                except Exception as error:
                    call_path = audit / f'{path.stem}.calls.json'
                    call_count = len(json.loads(call_path.read_text(encoding='utf-8'))) if call_path.exists() else 0
                    record = {'file': path.name, 'status': 'failed', 'error_type': type(error).__name__,
                              'overview_calls_attempted': call_count}
                records.append(record)
                save(audit / 'generation_manifest.json', {
                    'new_overview_calls_attempted': sum(r['overview_calls_attempted'] for r in records),
                    'review_analysis_calls': 0, 'records': records})
                print(json.dumps({'file': record['file'], 'status': record['status']}, ensure_ascii=False), flush=True)
    if not any(r['status'] == 'failed' for r in records) and (source / 'index.json').is_file():
        save(out / 'index.json', json.loads((source / 'index.json').read_text(encoding='utf-8')))
    return int(any(r['status'] == 'failed' for r in records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT / 'frontend/public/reference')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=2, choices=range(1, 4))
    args = parser.parse_args()
    return run_batch(args.input_dir, args.out_dir, args.audit_dir, args.workers)
