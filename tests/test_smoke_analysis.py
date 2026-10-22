"""Smoke CLI checks use synthetic responses and never call the API."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'smoke_analysis', Path(__file__).resolve().parents[1] / 'scripts/smoke_analysis.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeTests(unittest.TestCase):
    def test_required_glossary_missing_stops_before_api(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(smoke, 'ROOT', Path(tmp)), patch.object(
            smoke.sys, 'argv', ['smoke', '--require-glossary', '--output', 'out.json']
        ), patch.object(smoke, 'analyze_review_with_metrics') as analyze:
            with self.assertRaises(SystemExit) as error:
                smoke.main()
            self.assertEqual(error.exception.code, 2)
            analyze.assert_not_called()

    def test_required_glossary_checks_response_metrics(self):
        for loaded in (True, False):
            with self.subTest(loaded=loaded), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'docs').mkdir()
                (root / 'docs/slang_glossary.md').write_text('glossary', encoding='utf-8')
                (root / 'input.jsonl').write_text('{"id":"x","text":"sample"}\n', encoding='utf-8')
                output = SimpleNamespace(model_dump=lambda: {'items': []})
                with patch.object(smoke, 'ROOT', root), patch.object(smoke.sys, 'argv', [
                    'smoke', '--input', 'input.jsonl', '--require-glossary', '--output', 'out.json'
                ]), patch.object(smoke, 'analyze_review_with_metrics', return_value=(output, {'glossary_loaded': loaded})):
                    self.assertEqual(smoke.main(), 0 if loaded else 1)
                self.assertTrue((root / 'out.json').is_file())
