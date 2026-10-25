"""Data-integrity and rubric checks for the versioned reference (offline)."""
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
ROWS={r['id']:r for r in [json.loads(s) for s in (ROOT/'data/reference_gold64_v2.jsonl').read_text(encoding='utf-8').splitlines()]}
def pairs(rid):return {(x['category'],x['sentiment']) for x in ROWS[rid]['labels']}

class ConsistencyReferenceTests(unittest.TestCase):
    def test_strictness_without_discomfort_is_neutral(self):
        for rid in ['c03-2025-2-r07','c03-2026-1-r04','c03-2026-1-r07']:
            self.assertIn(('attendance','neutral'),pairs(rid));self.assertNotIn(('attendance','negative'),pairs(rid))
    def test_explicit_burden_and_risk_remain_negative(self):
        for rid in ['c03-2025-2-r01','c03-2025-2-r06','c03-2026-1-r01','c03-2026-1-r08']:
            self.assertIn(('attendance','negative'),pairs(rid))
    def test_assignment_feedback_vs_question_response(self):
        self.assertIn(('professor','negative'),pairs('c01-2026-1-r03'))
        self.assertNotIn(('delivery','negative'),pairs('c01-2026-1-r03'))
        self.assertIn(('delivery','negative'),pairs('c01-2025-2-r08'))
    def test_team_presentations_not_counted_twice(self):
        for rid in ['c04-2026-1-r04','c04-2026-1-r07']:
            self.assertFalse(any(c=='attendance' for c,s in pairs(rid)))
    def test_exam_type_and_time_are_separate(self):
        p=pairs('c01-2026-1-r07');self.assertIn(('exam','neutral'),p);self.assertIn(('exam','negative'),p)
    def test_grade_waiting_does_not_infer_bad_grade(self):
        self.assertNotIn(('grade','negative'),pairs('c02-2026-1-r08'))
    def test_prerequisite_time_has_correct_topic(self):
        self.assertIn(('workload','neutral'),pairs('c02-2025-2-r06'))
    def test_noise_rows_stay_empty(self):
        self.assertEqual(sum(not r['labels'] for r in ROWS.values()),8)
    def test_every_label_has_exact_source_evidence(self):
        self.assertEqual(len(ROWS),64)
        for r in ROWS.values():
            self.assertEqual(len(pairs(r['id'])),len(r['labels']))
            for x in r['labels']:self.assertIn(x['evidence'],r['text'])
    def test_current_semester_alone_not_a_change(self):
        p=next(x for x in ROWS['c01-2026-1-r08']['labels'] if x['category']=='workload' and x['sentiment']=='positive')
        self.assertFalse(p['mentions_change'])
    def test_cached_scores_reproduce_without_api_calls(self):
        spec=importlib.util.spec_from_file_location('rescore',ROOT/'scripts/rescore_consistency.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.rescore()
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['new_api_calls'],0)
    def test_evaluation_texts_not_embedded_in_prompt(self):
        from analysis.prompt import RULES,FEW_SHOT
        prompt=RULES+'\n'+FEW_SHOT
        for r in ROWS.values():
            self.assertNotIn(r['text'],prompt)
            self.assertNotIn(r['id'],prompt)

    def test_canonical_hash_preserves_content_and_ignores_crlf(self):
        from scripts.rescore_consistency import canonical_sha256
        self.assertEqual(canonical_sha256(b'one\ntwo\n'),canonical_sha256(b'one\r\ntwo\r\n'))
        self.assertNotEqual(canonical_sha256(b'one\ntwo\n'),canonical_sha256(b'one\nchanged\n'))

    def test_baseline_snapshot_is_independent_of_portal_results(self):
        from scripts import rescore_consistency
        from unittest.mock import patch
        original_glob=Path.glob
        def guarded_glob(path,pattern):
            if path.as_posix().endswith('/frontend/public/reference'):
                raise AssertionError('Historical rescore must not read mutable portal files')
            return original_glob(path,pattern)
        with patch.object(Path,'glob',guarded_glob):
            self.assertTrue(all(rescore_consistency.rescore()['checks'].values()))

if __name__=='__main__':unittest.main()
