"""Build overviews from saved result files. Never reanalyze reviews.

Use a staging directory first:
python scripts/build_overview_data.py --out-dir /absolute/path/to/staging --audit-dir /absolute/path/to/audit
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.llm import configured_settings
from analysis.overview_contract import Overview
from analysis.overview_generation import make_input, finalize
from analysis.overview_prompt import OVERVIEW_INSTRUCTIONS
from openai import OpenAI


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def generate(path, out, audit):
    source_bytes = path.read_bytes()
    source = json.loads(source_bytes)
    if source['meta']['failed'] or source['meta']['model'] == 'mock':
        raise ValueError('Only successful real-model source files are accepted')
    audience = 'learner' if path.stem.endswith('_all') else 'instructor'
    key, model, effort = configured_settings()
    started = time.perf_counter()
    settings = {'reasoning': {'effort': effort}}
    if effort == 'none': settings['temperature'] = 0
    with OpenAI(api_key=key, timeout=180, max_retries=0) as client:
        response = client.responses.parse(model=model, store=False, instructions=OVERVIEW_INSTRUCTIONS,
            input=json.dumps(make_input(source, audience), ensure_ascii=False),
            text_format=Overview, max_output_tokens=18000, **settings)
    if response.status != 'completed' or response.output_parsed is None:
        raise ValueError('Overview response was incomplete')
    raw = response.output_parsed.model_dump()
    save(audit / f'{path.stem}.raw.json', raw)
    overview, findings = finalize(raw, source, audience)
    result = {**source, 'overview': overview}
    assert {k: v for k, v in result.items() if k != 'overview'} == {k: v for k, v in source.items() if k != 'overview'}
    assert path.read_bytes() == source_bytes
    save(out / path.name, result)
    record = {'file': path.name, 'audience': audience, 'status': 'generated_needs_review' if findings else 'generated',
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(), 'model': response.model,
        'prompt_sha256': hashlib.sha256(OVERVIEW_INSTRUCTIONS.encode()).hexdigest(),
        'usage': response.usage.model_dump(), 'latency_ms': round((time.perf_counter()-started)*1000), 'findings': findings}
    save(audit / f'{path.stem}.generation.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT/'frontend/public/reference')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=2, choices=range(1, 4))
    args = parser.parse_args()
    if args.input_dir.resolve() == args.out_dir.resolve():
        parser.error('Generate to a separate staging directory before quality review')
    semester_files = sorted(args.input_dir.glob('*_202*.json'))
    merged_files = sorted(args.input_dir.glob('*_all.json'))
    if len(semester_files) != 8 or len(merged_files) != 4:
        parser.error('Expected the approved 8 semester files and 4 merged course files')
    files = semester_files + merged_files
    records = []
    # Instructor files first, then learner files.
    for batch in (files[:8], files[8:]):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = {pool.submit(generate, path, args.out_dir, args.audit_dir): path for path in batch}
            for job in as_completed(jobs):
                path = jobs[job]
                try:
                    record = job.result()
                except Exception as error:
                    # Do not log SDK request bodies or private settings.
                    record = {'file': path.name, 'status': 'failed', 'error_type': type(error).__name__}
                records.append(record)
                save(args.audit_dir/'generation_manifest.json', {'new_overview_calls_attempted':len(records), 'review_analysis_calls':0, 'records':records})
                print(json.dumps({k:v for k,v in record.items() if k not in ('usage','source_sha256','prompt_sha256')},ensure_ascii=False),flush=True)
    return int(any(r['status']=='failed' for r in records))


if __name__ == '__main__': raise SystemExit(main())
