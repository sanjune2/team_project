"""Evaluate the versioned 45-review set. Only text/semester reach the model."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import time

from .runtime import ROOT, enable_local_packages, load_private_env

enable_local_packages()
import pandas as pd
from .llm_schemas import LLMReviewOutput, Category, Sentiment
from typing import get_args


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def read_gold(path, expected_count=45):
    raw = Path(path).read_bytes()
    rows = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(f'평가 대상은 {expected_count}개여야 합니다. actual={len(rows)}')
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('정답 리뷰 ID가 중복됩니다.')
    for row in rows:
        if not isinstance(row['id'], str) or not row['id'] or not isinstance(row['text'], str) or not row['text'].strip():
            raise ValueError('정답 ID와 원문을 확인하세요.')
        seen = set()
        for label in row['labels']:
            pair = (label['category'], label['sentiment'])
            if pair in seen or pair[0] not in get_args(Category) or pair[1] not in get_args(Sentiment):
                raise ValueError(f"잘못되거나 중복된 라벨: {row['id']}")
            seen.add(pair)
            if not label['evidence'].strip() or label['evidence'] not in row['text']:
                raise ValueError(f"정답 근거가 원문에 없습니다: {row['id']}")
            for alt in label.get('accept_also', []):
                if alt['category'] not in get_args(Category) or alt['sentiment'] not in get_args(Sentiment):
                    raise ValueError('accept_also enum을 확인하세요.')
    return rows, hashlib.sha256(raw).hexdigest()


def choices(label):
    return {(label['category'], label['sentiment'])} | {
        (alt['category'], alt['sentiment']) for alt in label.get('accept_also', [])}


def match_labels(labels, items, category_only=False):
    """Maximum one-to-one matching; alternatives cannot earn double credit.

    Category extraction uses unique categories. Sentiment uses individual items.
    Prefer sentiment-consistent matches to resolve equal-size category matchings.
    """
    if category_only:
        groups = {}
        for label in labels:
            groups.setdefault(label['category'], []).append(label)
        left = list(groups.values())
        right = sorted({item['category'] for item in items})
        edges = [[(j, sum(any((right[j], p['sentiment']) in choices(g) for g in group)
                         for p in items if p['category'] == right[j]))
                  for j in range(len(right)) if any(c == right[j] for g in group for c, _ in choices(g))]
                 for group in left]
    else:
        edges = [[(j, 0) for j, item in enumerate(items)
                  if (item['category'], item['sentiment']) in choices(label)] for label in labels]

    @lru_cache(None)
    def solve(i, used):
        if i == len(edges):
            return (0, 0, ())
        best = solve(i + 1, used)
        for j, bonus in edges[i]:
            if used & (1 << j):
                continue
            count, score, pairs = solve(i + 1, used | (1 << j))
            candidate = (count + 1, score + bonus, ((i, j),) + pairs)
            if candidate[:2] > best[:2]:
                best = candidate
        return best
    pairs = list(solve(0, 0)[2])
    if category_only:
        return [(list(groups)[i], right[j]) for i, j in pairs]
    return pairs


def evaluate(gold, predictions):
    gold_ids = [r['id'] for r in gold]
    pred_ids = [r['id'] for r in predictions]
    if len(set(gold_ids)) != len(gold_ids) or len(set(pred_ids)) != len(pred_ids) or set(gold_ids) != set(pred_ids):
        raise ValueError('정답과 예측 ID는 중복 없이 정확히 일치해야 합니다.')
    by_id = {r['id']: r for r in predictions}
    review_rows, detail_rows, field_rows = [], [], []
    for row in gold:
        pred = by_id[row['id']]
        if pred['status'] not in {'ok', 'failed'}:
            raise ValueError('예측 status가 잘못되었습니다.')
        items = pred.get('items', []) if pred['status'] == 'ok' else []
        if pred['status'] == 'ok':
            LLMReviewOutput.model_validate({'items': items})
        labels = row['labels']
        category_pairs = match_labels(labels, items, True)
        item_pairs = match_labels(labels, items)
        expected_categories = {i['category'] for i in labels}
        actual_categories = {i['category'] for i in items}
        # For each matched category, penalize both missing and extra sentiments.
        sentiment_denominator = sum(max(sum(g['category'] == gc for g in labels),
                                        sum(p['category'] == pc for p in items)) for gc, pc in category_pairs)
        sentiment_correct = sum(1 for gi, pi in item_pairs
                                if (labels[gi]['category'], items[pi]['category']) in category_pairs)
        exact = sum(bool(i['evidence'].strip()) and i['evidence'] in row['text'] for i in items)
        metrics = pred.get('metrics', {})
        record = {'id': row['id'], 'status': pred['status'], 'tp': len(category_pairs),
                  'fp': len(actual_categories) - len(category_pairs),
                  'fn': len(expected_categories) - len(category_pairs),
                  'sentiment_correct': sentiment_correct, 'sentiment_total': sentiment_denominator,
                  'pair_correct': len(item_pairs), 'gold_items': len(labels), 'predicted_items': len(items),
                  'evidence_exact': exact, 'failed': int(pred['status'] == 'failed'),
                  'latency_ms': metrics.get('latency_ms'),
                  'merged_item_count': metrics.get('merged_item_count'),
                  'pair_exact': int(pred['status'] == 'ok' and len(item_pairs) == len(labels) == len(items))}
        review_rows.append(record)
        detail_rows.append({**record, 'gold_labels': labels, 'predicted_items_detail': items,
                            'missing_categories': sorted(expected_categories - {g for g, _ in category_pairs}),
                            'extra_categories': sorted(actual_categories - {p for _, p in category_pairs})})
        paired = {gi: items[pi] for gi, pi in item_pairs}
        for gi, label in enumerate(labels):
            actual = paired.get(gi)
            for field in ('condition', 'mentions_change'):
                if field not in label:
                    continue
                value = actual.get(field) if actual is not None else None
                field_rows.append({'id': row['id'], 'category': label['category'],
                                   'sentiment': label['sentiment'], 'field': field,
                                   'expected': label[field], 'predicted': value,
                                   'matched_item': actual is not None,
                                   'presence_correct': actual is not None and bool(value) == bool(label[field]),
                                   'literal_correct': actual is not None and value == label[field],
                                   'semantic_review': 'pending' if field == 'condition' else None})
    frame = pd.DataFrame(review_rows)
    totals = frame[['tp', 'fp', 'fn', 'sentiment_correct', 'sentiment_total', 'pair_correct',
                    'gold_items', 'predicted_items', 'evidence_exact', 'failed', 'pair_exact']].sum().to_dict()
    tp, fp, fn = (int(totals[k]) for k in ('tp', 'fp', 'fn'))
    merged = frame['merged_item_count'].dropna()
    fields = {}
    for field in ('condition', 'mentions_change'):
        entries = [r for r in field_rows if r['field'] == field]
        fields[field] = {'annotated_count': len(entries),
                         'missing_gold_count': int(totals['gold_items']) - len(entries),
                         'matched_item_count': sum(e['matched_item'] for e in entries),
                         'presence_accuracy': ratio(sum(e['presence_correct'] for e in entries), len(entries)),
                         'literal_accuracy': ratio(sum(e['literal_correct'] for e in entries), len(entries))}
    summary = {**{k: int(v) for k, v in totals.items()}, 'review_count': len(gold),
               'category_precision': ratio(tp, tp + fp), 'category_recall': ratio(tp, tp + fn),
               'category_f1': ratio(2 * tp, 2 * tp + fp + fn),
               'sentiment_accuracy': ratio(int(totals['sentiment_correct']), int(totals['sentiment_total'])),
               'evidence_exact_rate': ratio(int(totals['evidence_exact']), int(totals['predicted_items'])),
               'failure_rate': ratio(int(totals['failed']), len(gold)),
               'mean_latency_ms': float(frame['latency_ms'].dropna().mean()) if frame['latency_ms'].notna().any() else None,
               'timed_review_count': int(frame['latency_ms'].notna().sum()),
               'merged_item_distribution': {str(int(k)): int(v) for k, v in Counter(merged).items()},
               'merged_review_ids': frame.loc[frame['merged_item_count'].fillna(0) > 0, 'id'].tolist(),
               'merged_review_rate': ratio(int((merged > 0).sum()), len(merged)),
               'fields': fields}
    return {'summary': summary, 'reviews': detail_rows, 'field_review': field_rows}


def write_report(path, result, provenance):
    s = result['summary']
    def percent(value):
        return '측정 불가' if value is None else f'{value:.2%}'
    lines = ['# 45개 1차 분석 평가', '', f"- 평가 시각(UTC): {provenance['created_at']}",
             f"- 데이터: `{provenance['data_path']}` / SHA-256 `{provenance['data_sha256']}`",
             f"- 정답 상태: {provenance['label_status']}",
             '- 분석 함수의 실제 API 평가다. HTTP·웹 통합 검증은 포함하지 않는다.',
             '- 로컬 데이터 병합 후보는 포함하지 않았다.', '', '| 지표 | 결과 | 분모 또는 건수 |', '|---|---:|---|',
             f"| 리뷰 수 | {s['review_count']} | 전체 |",
             f"| 항목 정밀도 | {percent(s['category_precision'])} | TP {s['tp']} / FP {s['fp']} |",
             f"| 항목 재현율 | {percent(s['category_recall'])} | TP {s['tp']} / FN {s['fn']} |",
             f"| 항목 F1 | {percent(s['category_f1'])} | 리뷰별 고유 항목을 합산 |",
             f"| 감성 정확도 | {percent(s['sentiment_accuracy'])} | {s['sentiment_correct']}/{s['sentiment_total']} |",
             f"| 근거 원문 exact | {percent(s['evidence_exact_rate'])} | {s['evidence_exact']}/{s['predicted_items']} |",
             f"| 실패율 | {percent(s['failure_rate'])} | {s['failed']}/{s['review_count']} |",
             f"| 평균 처리 시간 | {s['mean_latency_ms']} ms | 성공·실패 포함 {s['timed_review_count']}개 |", '',
             '## 평가 규칙', '',
             '- 항목은 리뷰별 고유 category로 센다. accept_also는 한 정답의 대안이며 이중 정답으로 세지 않는다.',
             '- 최대 일대일 매칭을 사용한다. 감성은 매칭된 항목에서 정답·예측 감성 수 중 큰 수를 분모로 쓴다.',
             '- 실패 리뷰도 정답 항목을 FN으로 센다. 모든 예측 근거를 exact 비율의 분모로 쓴다.',
             '- 근거 exact는 원문의 부분 문자열인지 확인한다. 감성을 뒷받침하는지는 별도 사람 검토가 필요하다.',
             '- 누락된 condition·mentions_change 정답을 null·false로 간주하지 않는다.',
             '- condition 문자열 일치율은 진단 지표다. 조건 내용의 의미 정확도는 사람이 확인해야 한다.', '',
             '## 추가 지표', '',
             f"- merged_item_count 분포: `{json.dumps(s['merged_item_distribution'])}`",
             f"- 1개 이상 병합한 리뷰: {s['merged_review_ids']} / 비율 {percent(s['merged_review_rate'])}", '',
             '| 필드 | 명시 정답 수 | 정답 누락 수 | 항목·감성 매칭 수 | 유무 정확도 | 문자열/값 일치율 |',
             '|---|---:|---:|---:|---:|---:|']
    for name, value in s['fields'].items():
        lines.append(f"| {name} | {value['annotated_count']} | {value['missing_gold_count']} | {value['matched_item_count']} | {percent(value['presence_accuracy'])} | {percent(value['literal_accuracy'])} |")
    lines += ['', '명시된 condition은 모두 조건이 있는 사례이며 mentions_change 정답은 모두 true다.',
              '조건·변경이 없는 사례의 오탐률과 전체 정확도는 이 라벨만으로 계산할 수 없다.']
    lines += ['', '## 호출 조건', '', '```json', json.dumps(provenance, ensure_ascii=False, indent=2), '```', '',
              '## 경계 사례 및 표현 노출', '',
              '- c14·c15는 은어 사전에 패턴이 등록되어 있다. 독립적인 일반화 점수로 해석하지 않는다.',
              '- t02·c11은 few-shot과 표현 일부가 겹친다. 아래 제외 점수도 함께 본다.', '']
    for name, subset in result.get('subsets', {}).items():
        lines.append(f"- {name}: {subset['review_count']}개, 항목 F1 {percent(subset['category_f1'])}, 감성 {percent(subset['sentiment_accuracy'])}")
    lines += ['', '## 검토할 차이', '', '| ID | 누락 항목 | 추가 항목 | 감성 정답/분모 |', '|---|---|---|---|']
    for row in result['reviews']:
        if not row['pair_exact']:
            lines.append(f"| {row['id']} | {', '.join(row['missing_categories'])} | {', '.join(row['extra_categories'])} | {row['sentiment_correct']}/{row['sentiment_total']} |")
    lines += ['', '## 해석과 후속 확인', '', '- 라벨 교차 검토 완료 확인과 condition 의미 검토가 필요하다.',
              '- 실행 간 비교와 6·7번 진행 상태는 docs/eval_comparison.md를 확인한다.',
              '- 노션 완료 체크는 요구사항 전체를 검증한 뒤 처리한다.', '']
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='45개 기준 분석 평가. --live는 유료 API를 호출합니다.')
    parser.add_argument('--data', default='data/test_reviews.jsonl')
    parser.add_argument('--predictions', help='기존 실제 응답 JSON을 재평가')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', default='evaluation_v1.local.json')
    parser.add_argument('--report', default='docs/eval_v1.md')
    parser.add_argument('--env-file', help='비공개 환경 설정 경로. 값은 출력하지 않음')
    parser.add_argument('--model', help='비교 실험에서만 모델 설정을 재정의')
    parser.add_argument('--reasoning-effort', choices=['none', 'low', 'medium', 'high', 'xhigh', 'max'])
    parser.add_argument('--stop-on-error', action='store_true', help='비교 후보의 첫 실패에서 중단. 부분 점수는 만들지 않음')
    parser.add_argument('--label-status', default='제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.')
    args = parser.parse_args()
    if args.live == bool(args.predictions):
        parser.error('--live 또는 --predictions 중 하나를 지정하세요.')
    data_path = ROOT / args.data
    gold, digest = read_gold(data_path)
    provenance = {'created_at': datetime.now(timezone.utc).isoformat(), 'data_path': args.data,
                  'data_sha256': digest, 'label_status': args.label_status}
    (ROOT / args.output).parent.mkdir(parents=True, exist_ok=True)
    if args.live:
        if args.env_file:
            load_private_env(args.env_file)
        if args.model:
            os.environ['OPENAI_MODEL'] = args.model
        if args.reasoning_effort:
            os.environ['OPENAI_REASONING_EFFORT'] = args.reasoning_effort
        from .llm import analyze_review_with_metrics, LLMAnalysisError
        predictions = []
        for row in gold:
            started = time.perf_counter()
            try:
                parsed, metrics = analyze_review_with_metrics(row['text'], semester=row.get('semester'))
                prediction = {'id': row['id'], 'status': 'ok', 'items': parsed.model_dump()['items'], 'metrics': metrics}
            except (LLMAnalysisError, ValueError) as error:
                prediction = {'id': row['id'], 'status': 'failed', 'items': [], 'error': str(error),
                              'metrics': {'latency_ms': round((time.perf_counter() - started) * 1000)}}
            predictions.append(prediction)
            # Save after each request, preserving evidence if a run is interrupted.
            (ROOT / args.output).write_text(json.dumps({'provenance': provenance, 'predictions': predictions}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print(json.dumps({'id': row['id'], 'status': prediction['status']}, ensure_ascii=False), flush=True)
            if args.stop_on_error and prediction['status'] == 'failed':
                print('후보 호출 실패로 중단했습니다. 부분 결과는 전체 정확도로 계산하지 않습니다.', flush=True)
                return 2
    else:
        saved = json.loads((ROOT / args.predictions).read_text(encoding='utf-8'))
        if saved['provenance']['data_sha256'] != digest:
            raise ValueError('저장된 예측의 데이터 해시가 다릅니다.')
        provenance = saved['provenance']
        predictions = saved['predictions']
    successful_metrics = [p['metrics'] for p in predictions if p['status'] == 'ok']
    provenance['models'] = sorted({m['model'] for m in successful_metrics})
    provenance['prompt_sha256'] = sorted({m['prompt_sha256'] for m in successful_metrics})
    provenance['reasoning_effort'] = sorted({m['reasoning_effort'] for m in successful_metrics})
    provenance['temperature'] = 0 if provenance['reasoning_effort'] == ['none'] else None
    provenance['max_retries'] = 0
    provenance['timeout_seconds'] = 30
    provenance['max_output_tokens'] = 4000
    provenance['usage_total'] = {k: sum(m.get('usage', {}).get(k, 0) for m in successful_metrics if m.get('usage'))
                               for k in ('input_tokens', 'output_tokens', 'total_tokens')}
    result = evaluate(gold, predictions)
    result['subsets'] = {}
    for name, excluded in [('exclude_glossary_c14_c15', {'c14', 'c15'}),
                           ('exclude_overlap_t02_c11', {'t02', 'c11'}),
                           ('exclude_all_four', {'c14', 'c15', 't02', 'c11'})]:
        result['subsets'][name] = evaluate([r for r in gold if r['id'] not in excluded],
                                           [p for p in predictions if p['id'] not in excluded])['summary']
    (ROOT / args.output).write_text(json.dumps({'provenance': provenance, 'predictions': predictions, **result}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    write_report(ROOT / args.report, result, provenance)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    return int(result['summary']['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
