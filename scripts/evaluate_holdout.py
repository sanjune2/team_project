"""동결된 합성 holdout 20개 평가. 기본 동작은 준비이며 실행은 명시적으로 선택한다."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.evaluate import read_gold
from analysis.overview_runner import save
from analysis.prompt import build_instructions
from scripts.rescore_consistency import score


def sha(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def prepare(out, model, effort):
    out = Path(out)
    if (out / 'predictions.json').exists() or (out / 'run_started.json').exists():
        raise ValueError('이미 실행한 평가 폴더입니다. 기존 결과를 보존하세요.')
    gold_path = ROOT / 'data/holdout_reviews.jsonl'
    gold, _ = read_gold(gold_path, expected_count=20)
    original_manifest = json.loads((ROOT / 'data/holdout_reviews_manifest.json').read_text(encoding='utf-8'))
    if sha(gold_path.read_bytes()) != original_manifest['sha256']:
        raise ValueError('동결한 holdout 원문 또는 라벨이 변경되었습니다.')
    glossary = (ROOT / 'docs/slang_glossary.md').read_text(encoding='utf-8')
    instructions = build_instructions(glossary)
    manifest = {'review_count': 20, 'gold_items': sum(len(r['labels']) for r in gold),
                'data_sha256_lf': sha(gold_path.read_bytes()), 'model': model, 'reasoning_effort': effort,
                'temperature': 0 if effort == 'none' else None, 'timeout_seconds': 30, 'max_retries': 0,
                'max_output_tokens': 4000, 'prompt_version': 'v3',
                'prompt_sha256': hashlib.sha256(instructions.encode()).hexdigest(),
                'glossary_sha256_lf': sha(glossary.encode()),
                'schema_sha256_lf': sha((ROOT / 'analysis/llm_schemas.py').read_bytes()),
                'label_status': 'AI 지원 합성 초안 라벨 대비 잠정 평가. 독립 사람 라벨 검수 미완료.',
                'original_protocol_target': 'v2 (역사적 계획)', 'this_run_target': '현재 main의 v3',
                'original_manifest_preserved': True, 'new_api_calls_attempted': 0}
    save(out / 'manifest.json', manifest)
    (out / 'prompt_frozen.txt').write_text(instructions, encoding='utf-8')
    return gold, manifest


def run(out, *, allow_ai_draft_labels=False):
    if not allow_ai_draft_labels:
        raise ValueError('사람 검수 전 잠정 평가에는 --allow-ai-draft-labels가 필요합니다.')
    from analysis.llm import analyze_review_with_metrics, configured_settings
    _, model, effort = configured_settings()
    gold, manifest = prepare(out, model, effort)
    out = Path(out)
    save(out / 'run_started.json', {'review_ids': [r['id'] for r in gold], 'retries': 0})
    predictions = []
    for row in gold:
        try:
            parsed, metrics = analyze_review_with_metrics(row['text'], semester=row.get('semester'))
            if metrics['prompt_sha256'] != manifest['prompt_sha256'] or metrics['reasoning_effort'] != effort:
                raise ValueError('평가 중 프롬프트 또는 설정이 변경되었습니다.')
            prediction = {'id': row['id'], 'status': 'ok', 'items': parsed.model_dump()['items'], 'metrics': metrics}
        except Exception as error:
            prediction = {'id': row['id'], 'status': 'failed', 'items': [], 'error_type': type(error).__name__}
        predictions.append(prediction)
        save(out / 'predictions.json', predictions)
        manifest['new_api_calls_attempted'] = len(predictions)
        save(out / 'manifest.json', manifest)
        print(json.dumps({'id': row['id'], 'status': prediction['status']}, ensure_ascii=False), flush=True)
    result = score(gold, predictions)
    save(out / 'evaluation.json', result)
    summary = result['summary']
    (out / 'report.md').write_text(
        '# 합성 holdout 20개 잠정 평가\n\n' + manifest['label_status'] + '\n\n'
        + f"모델 {model}, 프롬프트 v3, 새 호출 {len(predictions)}회. 기존 평가와 별도 실행.\n\n"
        + f"- 평가 분모: {len(gold)}개, 정답 item {manifest['gold_items']}개\n"
        + f"- 항목 F1: {summary['category_f1']:.2%}\n"
        + f"- 항목+감성 F1: {summary['pair_f1']:.2%}\n"
        + f"- 리뷰 완전 일치: {summary['pair_exact']}/{len(gold)}\n"
        + f"- 근거 원문 일치: {summary['evidence_exact']}/{summary['predicted_items']}\n"
        + f"- 조건 유무·문구 일치: {summary['fields']['condition']['presence_accuracy']:.2%} / {summary['fields']['condition']['literal_accuracy']:.2%} (의미 사람 검토 별도)\n"
        + f"- 변경 표시 일치: {summary['fields']['mentions_change']['literal_accuracy']:.2%}\n"
        + f"- 실패: {summary['failed']}/{len(gold)}\n\n"
        + '라벨·프롬프트를 이 결과에 맞춰 수정하지 않았습니다. 사람이 확정한 정답, 실사용 정확도 또는 학습 데이터 미포함을 보장하는 평가가 아닙니다.\n', encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir', type=Path, required=True)
    p.add_argument('--run', action='store_true')
    p.add_argument('--allow-ai-draft-labels', action='store_true')
    p.add_argument('--model', default='gpt-6-luna', help='준비 모드의 모델명. 실제 실행은 .env 사용')
    p.add_argument('--reasoning-effort', default='none', help='준비 모드 설정. 실제 실행은 .env 사용')
    args = p.parse_args()
    if args.run:
        result = run(args.out_dir, allow_ai_draft_labels=args.allow_ai_draft_labels)
        print(json.dumps(result['summary'], ensure_ascii=False))
        return int(bool(result['summary']['failed']))
    _, manifest = prepare(args.out_dir, args.model, args.reasoning_effort)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
