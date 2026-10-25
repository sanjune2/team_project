from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from analysis import overview_runner as runner

ROOT = Path(__file__).resolve().parents[1]


def response(value=None, status='completed', reason=None):
    return SimpleNamespace(status=status, model='test', usage=None,
        output_text=json.dumps(value) if value is not None else '{',
        incomplete_details=SimpleNamespace(reason=reason))


class OverviewRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.path = base / 'input/c01_2025-2.json'
        self.out, self.audit = base / 'output', base / 'audit'
        self.path.parent.mkdir()
        self.source = json.loads((ROOT / 'frontend/public/reference/c01_2025-2.json').read_text(encoding='utf-8'))
        # 한 항목만 남겨 분할 경계와 부분 실패를 검사한다. 모델 품질을 평가하는 fixture가 아니다.
        code = self.source['overview']['categories'][0]['category']
        label = runner.make_input(self.source, 'instructor')['category_labels'][code]
        self.source['summary_by_category'] = [r for r in self.source['summary_by_category'] if r['category'] == code]
        for r in self.source['reviews']:
            r['items'] = [i for i in r['items'] if i['category'] == code]
        ov = self.source['overview']
        ov['categories'] = [c for c in ov['categories'] if c['category'] == code]
        for side in ('left', 'right'):
            ov[side] = [a for a in ov[side] if a['keyword'] == label]
        self.path.write_text(json.dumps(self.source), encoding='utf-8')
        self.before = self.path.read_bytes()
        self.raw = deepcopy(ov)

    def generate(self, responses):
        client = MagicMock()
        client.__enter__.return_value = client
        client.responses.create.side_effect = responses
        with patch.object(runner, 'OpenAI', return_value=client), patch.object(runner, 'configured_settings', return_value=('fake', 'test', 'none')):
            result = runner.generate(self.path, self.out, self.audit)
        return result, client

    def split_responses(self):
        summary = {k: v for k, v in self.raw.items() if k != 'categories'}
        return [response(status='incomplete', reason='max_output_tokens'), response(summary),
                response({'categories': self.raw['categories']})]

    def test_completed_response_uses_one_call_and_preserves_source(self):
        record, client = self.generate([response(self.raw)])
        self.assertEqual(record['overview_calls_attempted'], 1)
        self.assertFalse(record['split_fallback'])
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertTrue((self.out / self.path.name).is_file())
        payload = json.loads(client.responses.create.call_args.kwargs['input'])
        self.assertTrue(all('text' not in r for r in payload['reviews']))

    def test_truncated_json_is_split_before_parsing(self):
        record, client = self.generate(self.split_responses())
        self.assertTrue(record['split_fallback'])
        self.assertEqual(record['overview_calls_attempted'], 3)
        self.assertEqual(self.path.read_bytes(), self.before)
        category_input = json.loads(client.responses.create.call_args.kwargs['input'])
        self.assertEqual(len(category_input['summary_by_category']), 1)

    def test_split_truncation_keeps_existing_output_and_source(self):
        self.out.mkdir()
        destination = self.out / self.path.name
        destination.write_text('existing-output', encoding='utf-8')
        responses = self.split_responses()
        responses[-1] = response(status='incomplete', reason='max_output_tokens')
        with self.assertRaises(runner.OverviewTruncated):
            self.generate(responses)
        self.assertEqual(destination.read_text(encoding='utf-8'), 'existing-output')
        self.assertEqual(self.path.read_bytes(), self.before)

    def test_wrong_category_is_rejected_without_partial_publish(self):
        responses = self.split_responses()
        responses[-1] = response({'categories': []})
        with self.assertRaisesRegex(ValueError, 'missing or extra'):
            self.generate(responses)
        self.assertFalse((self.out / self.path.name).exists())

    def test_content_filter_does_not_trigger_split(self):
        with self.assertRaisesRegex(ValueError, 'did not complete'):
            self.generate([response(status='incomplete', reason='content_filter')])
        self.assertEqual(len(json.loads((self.audit / 'c01_2025-2.calls.json').read_text(encoding='utf-8'))), 1)

    def test_request_error_is_counted_without_private_message(self):
        with self.assertRaises(RuntimeError):
            self.generate([RuntimeError('not-log-this-key')])
        text = (self.audit / 'c01_2025-2.calls.json').read_text(encoding='utf-8')
        self.assertNotIn('not-log-this-key', text)
        self.assertEqual(json.loads(text)[0]['status'], 'failed')

    def test_paths_are_validated_before_api_calls(self):
        with patch.object(runner, 'OpenAI') as client:
            with self.assertRaises(ValueError):
                runner.run_batch(self.path.parent, self.path.parent, self.audit)
            client.assert_not_called()

    def test_reference_overview_only_delegates_without_review_analysis(self):
        spec = importlib.util.spec_from_file_location('build_reference_test', ROOT / 'scripts/build_reference_data.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, 'argv', ['build_reference_data.py', '--overview-only', '--overview-out', str(self.out), '--overview-audit', str(self.audit)]), patch.object(runner, 'run_batch', return_value=0) as batch, patch.object(module, 'call_analyze') as analyze:
            self.assertEqual(module.main(), 0)
            batch.assert_called_once()
            analyze.assert_not_called()

    def test_strict_json_schema_requires_nullable_basis(self):
        schema = runner.strict_schema(runner.Overview)['schema']
        advice = schema['$defs']['Advice']
        self.assertIn('basis', advice['required'])
        self.assertFalse(advice['additionalProperties'])


if __name__ == '__main__':
    unittest.main()
