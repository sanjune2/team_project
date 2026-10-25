import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('holdout_runner_test', ROOT / 'scripts/evaluate_holdout.py')
holdout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(holdout)


class HoldoutRunnerTests(unittest.TestCase):
    def test_prepare_freezes_twenty_without_calling_model(self):
        with tempfile.TemporaryDirectory() as temp, patch('analysis.llm.analyze_review_with_metrics') as analyze:
            rows, manifest = holdout.prepare(temp, 'test-model', 'none')
            self.assertEqual(len(rows), 20)
            self.assertEqual(manifest['gold_items'], 22)
            self.assertEqual(manifest['new_api_calls_attempted'], 0)
            self.assertIn('잠정', manifest['label_status'])
            self.assertTrue((Path(temp) / 'prompt_frozen.txt').is_file())
            analyze.assert_not_called()

    def test_existing_run_is_not_overwritten_or_recalled(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'run_started.json'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '이미 실행'):
                holdout.prepare(temp, 'test-model', 'none')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {})

    def test_draft_run_requires_explicit_acknowledgment(self):
        with tempfile.TemporaryDirectory() as temp, patch('analysis.llm.analyze_review_with_metrics') as analyze:
            with self.assertRaisesRegex(ValueError, 'allow-ai-draft-labels'):
                holdout.run(temp)
            analyze.assert_not_called()


if __name__ == '__main__':
    unittest.main()
