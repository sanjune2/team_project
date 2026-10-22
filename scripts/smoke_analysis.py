"""Call the real analysis function with synthetic inputs, without HTTP."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.llm import analyze_review_with_metrics, LLMAnalysisError


def main():
    parser = argparse.ArgumentParser(description='실제 유료 API로 가상 리뷰를 분석합니다.')
    parser.add_argument('--input', default='data/smoke_reviews.jsonl')
    parser.add_argument('--output', required=True, help='실제 응답을 저장할 JSON 파일')
    parser.add_argument('--require-glossary', action='store_true', help='은어 사전 로딩을 필수로 확인')
    args = parser.parse_args()
    glossary = ROOT / 'docs/slang_glossary.md'
    if args.require_glossary and (not glossary.is_file() or not glossary.read_text(encoding='utf-8').strip()):
        parser.error('필수 은어 사전이 없거나 비어 있습니다.')
    source = ROOT / args.input
    target = ROOT / args.output
    rows = [json.loads(line) for line in source.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    results = []
    for row in rows:
        record = {'id': row['id']}
        try:
            parsed, metrics = analyze_review_with_metrics(row['text'])
            record.update(status='ok', items=parsed.model_dump()['items'], metrics=metrics)
        except (LLMAnalysisError, ValueError) as error:
            record.update(status='failed', error=str(error))
        results.append(record)
        print(json.dumps({'id':row['id'], 'status':record['status'],
            'glossary_loaded': record.get('metrics', {}).get('glossary_loaded')},ensure_ascii=False),flush=True)
        if record['status'] == 'failed':
            break
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'mode':'live_openai','scope':'analysis_function_only',
        'planned':len(rows),'reviews':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if rows and len(results)==len(rows) and all(
        r['status']=='ok' and (not args.require_glossary or r['metrics'].get('glossary_loaded') is True)
        for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
