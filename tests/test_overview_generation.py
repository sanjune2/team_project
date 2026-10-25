from copy import deepcopy
import json
from pathlib import Path
import unittest

from analysis.overview_generation import finalize, make_input, policy_findings

ROOT = Path(__file__).resolve().parents[1]


class OverviewGenerationTests(unittest.TestCase):
    def setUp(self):
        self.result=json.loads((ROOT/'frontend/public/reference/c01_2025-2.json').read_text(encoding='utf-8'))
        self.raw=deepcopy(self.result['overview'])

    def test_input_omits_original_text_and_normalizes_explicit_slang(self):
        self.result['reviews'][0]['items'][0]['summary']='에쁠과 팀플에 대한 의견'
        value=make_input(self.result,'instructor')
        self.assertNotIn('text',value['reviews'][0])
        self.assertIn('A+과 팀 프로젝트',value['reviews'][0]['items'][0]['summary'])

    def test_basis_tokens_use_verified_unique_ids(self):
        item=self.raw['left'][0]
        item['text']='관련 평가가 {basis}건 있었어요.'
        item['review_ids'] += [item['review_ids'][0], 'not-a-review']
        overview, findings=finalize(self.raw,self.result,'instructor')
        self.assertEqual(overview['left'][0]['text'],'관련 평가가 4건 있었어요.')
        self.assertTrue(any(x.get('requires_text_review') for x in findings))

    def test_small_sample_instructor_advice_is_flagged(self):
        self.raw['right'][-1]['text']='학점 의견이 1건 있어 검토해 볼 수 있어요.'
        self.assertTrue(any(x['issue']=='small_sample_recommendation' for x in policy_findings(self.raw)))

    def test_student_preference_in_instructor_advice_is_flagged(self):
        self.raw['right'][0]['text']='보고서 쓰기를 싫어하는 경우에 관한 의견이 5건 있었어요.'
        self.assertTrue(any(x['issue']=='student_condition_in_instructor_advice' for x in policy_findings(self.raw)))

    def test_learner_recommendation_form_is_required(self):
        self.raw['audience']='learner';self.raw['suggestion']=None
        self.raw['left'][0]['text']='관련 의견이 4건 있었어요.'
        self.assertTrue(any(x['issue']=='learner_recommendation_form' for x in policy_findings(self.raw)))

    def test_suggestion_is_short_and_avoids_repeated_hedging(self):
        self.raw['suggestion']='살펴볼 수 있어요. 점검해 볼 수 있어요.'
        self.assertTrue(any(x['issue']=='suggestion_length_or_repetition' for x in policy_findings(self.raw)))

    def test_finalization_never_changes_review_analysis(self):
        before=deepcopy(self.result)
        finalize(self.raw,self.result,'instructor')
        self.assertEqual(self.result,before)

    def test_missing_count_in_detail_is_filled_without_a_model_call(self):
        self.raw['categories'][0]['groups'][0]['detail']='과제 작업에 시간이 오래 걸린다는 의견이 있었어요.'
        overview, _=finalize(self.raw,self.result,'instructor')
        detail=overview['categories'][0]['groups'][0]['detail']
        self.assertEqual(detail,'리뷰 5건에서는 과제 작업에 시간이 오래 걸린다는 의견이 있었어요.')


if __name__=='__main__': unittest.main()
