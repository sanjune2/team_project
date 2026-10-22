from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.llm import analyze_review_with_metrics, LLMAnalysisError, merge_same_pairs
from analysis.llm_schemas import LLMReviewOutput, LLMItem, LLMWireOutput
from analysis.runtime import load_private_env
from pydantic import ValidationError


ITEM = {"category":"delivery", "sentiment":"positive", "summary":"설명이 쉽다는 의견", "evidence":"설명이 쉬워요", "keywords":[], "condition":None, "mentions_change":False}


class LLMConnectTests(unittest.TestCase):
    def test_repeated_pairs_merge_without_joining_evidence(self):
        first = LLMItem.model_validate({**ITEM, 'keywords':['설명'], 'condition':'처음 듣는 경우'})
        second = LLMItem.model_validate({**ITEM, 'summary':'예시가 구체적이라는 의견',
            'evidence':'예시가 구체적이라 이해하기 쉬워요', 'keywords':['설명','예시'],
            'condition':None, 'mentions_change':True})
        opposite = LLMItem.model_validate({**ITEM, 'sentiment':'negative'})
        wire = LLMWireOutput(items=[first, second, opposite])
        client = self.fake_client(wire)
        with patch('analysis.llm.configured_settings',return_value=('fake','test-model','none')), patch('analysis.llm.OpenAI',return_value=client):
            parsed, _ = analyze_review_with_metrics('설명이 쉬워요. 예시가 구체적이라 이해하기 쉬워요')
        self.assertEqual(len(parsed.items), 2)
        self.assertEqual(parsed.items[0].evidence, second.evidence)
        self.assertIn(first.summary, parsed.items[0].summary)
        self.assertIn(second.summary, parsed.items[0].summary)
        self.assertEqual(parsed.items[0].keywords, ['설명','예시'])
        self.assertEqual(parsed.items[0].condition, first.condition)
        self.assertTrue(parsed.items[0].mentions_change)
        self.assertEqual(first.summary, ITEM['summary'])

    def test_strict_schema_fields_are_required_and_backend_fields_absent(self):
        schema = LLMItem.model_json_schema()
        self.assertEqual(set(schema["properties"]), set(schema["required"]))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(len(schema["properties"]["category"]["enum"]), 10)
        for field in ITEM:
            row = dict(ITEM); row.pop(field)
            with self.assertRaises(ValidationError):
                LLMItem.model_validate(row)
        with self.assertRaises(ValidationError):
            LLMItem.model_validate({**ITEM, "evidence_verified": True})

    def test_bad_labels_keywords_and_duplicate_pairs_rejected(self):
        for update in ({"category":"overall"}, {"sentiment":"mixed"}, {"keywords":["a"]*4}, {"keywords":["a","a"]}, {"summary":"a\nb"}, {"mentions_change":1}, {"condition":" "}):
            with self.subTest(update=update), self.assertRaises(ValidationError):
                LLMItem.model_validate({**ITEM, **update})
        with self.assertRaises(ValidationError):
            LLMReviewOutput.model_validate({"items":[ITEM, ITEM]})
        output = LLMReviewOutput.model_validate({"items":[ITEM, {**ITEM,"sentiment":"negative"}]})
        self.assertEqual(len(output.items), 2)
        self.assertEqual(LLMReviewOutput.model_validate({"items":[]}).items, [])

    def test_private_settings_no_execution_and_process_values_win(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_MODEL":"existing"}, clear=True):
            env = Path(tmp)/".env"
            env.write_text('\ufeffOPENAI_API_KEY="fake-unit-key"\nOPENAI_MODEL=other\nOTHER_SECRET=no\nUSE_MOCK=false\n',encoding="utf-8")
            load_private_env(env)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "fake-unit-key")
            self.assertEqual(os.environ["OPENAI_MODEL"], "existing")
            self.assertNotIn("OTHER_SECRET", os.environ)

    def fake_client(self, parsed=None, status="completed"):
        client = MagicMock()
        client.__enter__.return_value = client
        client.responses.parse.return_value = SimpleNamespace(status=status, output_parsed=parsed, model="test-model", usage=None)
        return client

    def test_request_shape_no_label_leak_and_temperature_compatibility(self):
        parsed = LLMReviewOutput.model_validate({"items":[ITEM]})
        for effort in ("none", "low"):
            client = self.fake_client(parsed)
            with patch("analysis.llm.configured_settings",return_value=("fake","test-model",effort)), patch("analysis.llm.OpenAI",return_value=client):
                result, metrics = analyze_review_with_metrics("설명이 쉬워요", semester="26-1")
            args = client.responses.parse.call_args.kwargs
            self.assertFalse(args["store"])
            self.assertEqual(args["input"], "설명이 쉬워요")
            self.assertEqual(args["reasoning"], {"effort":effort})
            self.assertEqual("temperature" in args, effort == "none")
            self.assertEqual(result.items[0].category,"delivery")

    def test_invalid_input_never_calls_network(self):
        with patch("analysis.llm.OpenAI") as client:
            for text in ("", "   ", "a"*3001, None, True):
                with self.assertRaises(ValueError):
                    analyze_review_with_metrics(text)
            client.assert_not_called()

    def test_refusal_incomplete_and_error_messages_do_not_expose_sdk_text(self):
        for status in ("completed", "incomplete"):
            client = self.fake_client(None, status)
            with patch("analysis.llm.configured_settings",return_value=("fake","test-model","none")), patch("analysis.llm.OpenAI",return_value=client):
                with self.assertRaises(LLMAnalysisError):
                    analyze_review_with_metrics("설명이 쉬워요")
        client = self.fake_client()
        client.responses.parse.side_effect = RuntimeError("sensitive-request-body")
        with patch("analysis.llm.configured_settings",return_value=("fake","test-model","none")), patch("analysis.llm.OpenAI",return_value=client):
            with self.assertRaises(LLMAnalysisError) as caught:
                analyze_review_with_metrics("설명이 쉬워요")
        self.assertNotIn("sensitive", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
