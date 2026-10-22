import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analysis.evaluate import evaluate, match_labels, read_gold, main
from analysis.llm import LLMAnalysisError
from analysis.llm_schemas import LLMReviewOutput


def item(category='exam', sentiment='positive', evidence='좋다'):
    return dict(category=category, sentiment=sentiment, evidence=evidence,
                summary='평가 의견', keywords=[], condition=None, mentions_change=False)


def label(category='exam', sentiment='positive', **extra):
    return dict(category=category, sentiment=sentiment, evidence='좋다', **extra)


class EvaluationTests(unittest.TestCase):
    def run_case(self, labels, items, status='ok'):
        return evaluate([{'id': 'a', 'text': '좋다. 어렵다.', 'labels': labels}],
                        [{'id': 'a', 'status': status, 'items': items,
                          'metrics': {'latency_ms': 100, 'merged_item_count': 0}}])

    def test_wrong_sentiment_keeps_category_credit(self):
        s = self.run_case([label()], [item(sentiment='negative')])['summary']
        self.assertEqual((s['tp'], s['fp'], s['fn']), (1, 0, 0))
        self.assertEqual(s['sentiment_accuracy'], 0)

    def test_same_category_mixed_sentiments_count_category_once(self):
        s = self.run_case([label(), label(sentiment='negative')],
                          [item(), item(sentiment='negative')])['summary']
        self.assertEqual(s['tp'], 1)
        self.assertEqual((s['sentiment_correct'], s['sentiment_total']), (2, 2))

    def test_extra_sentiment_penalized(self):
        s = self.run_case([label()], [item(), item(sentiment='negative')])['summary']
        self.assertEqual(s['sentiment_accuracy'], .5)

    def test_alternative_does_not_earn_double_credit(self):
        gold = [label('grade', accept_also=[{'category': 'general_impression', 'sentiment': 'positive'}])]
        s = self.run_case(gold, [item('grade'), item('general_impression')])['summary']
        self.assertEqual((s['tp'], s['fp'], s['fn']), (1, 1, 0))
        self.assertEqual(self.run_case(gold, [item('general_impression')])['summary']['sentiment_accuracy'], 1)

    def test_matching_avoids_greedy_trap(self):
        gold = [label('grade', accept_also=[{'category': 'exam', 'sentiment': 'positive'}]), label('exam')]
        pairs = match_labels(gold, [item('exam'), item('grade')])
        self.assertEqual(len(pairs), 2)

    def test_failed_review_counts_missing_gold_and_latency(self):
        s = self.run_case([label()], [], 'failed')['summary']
        self.assertEqual((s['fn'], s['failure_rate'], s['mean_latency_ms']), (1, 1, 100))

    def test_empty_gold_has_no_fabricated_accuracy(self):
        s = self.run_case([], [])['summary']
        self.assertIsNone(s['category_f1'])
        self.assertIsNone(s['evidence_exact_rate'])
        self.assertEqual(s['pair_exact'], 1)

    def test_exact_evidence_not_gold_span_equality(self):
        s = self.run_case([label()], [item(evidence='어렵다')])['summary']
        self.assertEqual(s['evidence_exact_rate'], 1)
        s = self.run_case([label()], [item(evidence='없는 문구')])['summary']
        self.assertEqual(s['evidence_exact_rate'], 0)

    def test_missing_optional_gold_not_assumed_false(self):
        fields = self.run_case([label()], [item()])['summary']['fields']
        self.assertEqual(fields['mentions_change']['annotated_count'], 0)
        self.assertIsNone(fields['mentions_change']['literal_accuracy'])
        self.assertEqual(fields['condition']['missing_gold_count'], 1)

    def test_condition_presence_and_content_separate(self):
        predicted = item()
        predicted['condition'] = '초보자일 때'
        result = self.run_case([label(condition='입문자인 경우')], [predicted])
        s = result['summary']['fields']['condition']
        self.assertEqual(s['presence_accuracy'], 1)
        self.assertEqual(s['literal_accuracy'], 0)
        self.assertEqual(result['field_review'][0]['semantic_review'], 'pending')

    def test_duplicate_prediction_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([{'id': 'a', 'text': '좋다', 'labels': []}],
                     [{'id': 'a', 'status': 'ok'}, {'id': 'a', 'status': 'ok'}])

    def test_missing_prediction_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            evaluate([{'id': 'a', 'text': '좋다', 'labels': []}], [])

    def test_count_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'gold.jsonl'
            path.write_text(json.dumps({'id': 'a', 'text': '좋다', 'labels': []}), encoding='utf-8')
            with self.assertRaises(ValueError):
                read_gold(path)
            self.assertEqual(len(read_gold(path, expected_count=1)[0]), 1)

    def test_live_runner_never_passes_labels_to_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gold = [{'id': f'r{i}', 'text': '좋다', 'semester': '25-1', 'labels': [label()],
                     'tags': ['single'], 'note': 'secret-gold'} for i in range(45)]
            (root / 'gold.jsonl').write_text('\n'.join(json.dumps(r) for r in gold), encoding='utf-8')
            metrics = {'model': 'test_model', 'prompt_sha256': 'test_hash', 'reasoning_effort': 'none',
                       'latency_ms': 1, 'merged_item_count': 0, 'usage': None}
            with patch('analysis.evaluate.ROOT', root), patch('sys.argv', ['evaluate', '--live', '--data', 'gold.jsonl']), \
                 patch('analysis.llm.analyze_review_with_metrics', return_value=(LLMReviewOutput(items=[item()]), metrics)) as call, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            self.assertEqual(call.call_count, 45)
            for invocation in call.call_args_list:
                self.assertEqual(invocation.args, ('좋다',))
                self.assertEqual(invocation.kwargs, {'semester': '25-1'})
            saved = json.loads((root / 'evaluation_v1.local.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['summary']['review_count'], 45)

    def test_candidate_first_failure_does_not_publish_partial_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gold.jsonl').write_text('\n'.join(json.dumps({'id': str(i), 'text': '좋다', 'labels': []}) for i in range(45)), encoding='utf-8')
            with patch('analysis.evaluate.ROOT', root), \
                 patch('sys.argv', ['evaluate', '--live', '--stop-on-error', '--data', 'gold.jsonl']), \
                 patch('analysis.llm.analyze_review_with_metrics', side_effect=LLMAnalysisError('test failure')) as call, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 2)
            self.assertEqual(call.call_count, 1)
            self.assertFalse((root / 'docs/eval_v1.md').exists())
            self.assertNotIn('summary', json.loads((root / 'evaluation_v1.local.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
