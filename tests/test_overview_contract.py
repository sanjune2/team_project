"""Validate the two Step 7 trials and meaningful failure cases without model calls."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from analysis.overview_contract import validate_overview

ROOT = Path(__file__).resolve().parents[1]


class OverviewContractTests(unittest.TestCase):
    def setUp(self):
        self.result = json.loads((ROOT/'frontend/public/reference/c01_2025-2.json').read_text(encoding='utf-8'))
        self.overview = self.result['overview']

    def test_two_trials_match_current_reference_and_have_no_invalid_ids(self):
        for filename, audience in [('c01_2025-2.json', 'instructor'), ('c01_all.json', 'learner')]:
            with self.subTest(filename=filename):
                result = json.loads((ROOT/'frontend/public/reference'/filename).read_text(encoding='utf-8'))
                overview = result['overview']
                checked, issues = validate_overview(overview, result, audience=audience)
                self.assertEqual(issues, [])
                self.assertEqual(checked, overview)
                for c in checked['categories']:
                    sizes = [g['basis'] for g in c['groups']]
                    self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_invalid_advice_id_is_removed_and_requires_text_review(self):
        self.overview['left'][0]['review_ids'].append('not-in-this-file')
        checked, issues = validate_overview(self.overview, self.result, audience='instructor')
        self.assertNotIn('not-in-this-file', checked['left'][0]['review_ids'])
        self.assertTrue(issues[0]['requires_text_review'])
        self.assertEqual(issues[0]['removed_ids'], ['not-in-this-file'])

    def test_wrong_sentiment_ids_are_not_counted(self):
        item = self.overview['right'][0]
        item['keyword'] = '전달력'
        item['review_ids'] = ['c01-2025-2-r01']  # positive delivery only
        checked, issues = validate_overview(self.overview, self.result, audience='instructor')
        self.assertLess(len(checked['right']), len(self.overview['right']))
        self.assertTrue(issues)

    def test_duplicate_ids_do_not_inflate_basis(self):
        item = self.overview['left'][0]
        expected = len(item['review_ids'])
        item['review_ids'] *= 2
        item['basis'] = 999
        checked, _ = validate_overview(self.overview, self.result, audience='instructor')
        self.assertEqual(checked['left'][0]['basis'], expected)

    def test_zero_basis_group_is_removed_and_groups_sorted(self):
        category = next(c for c in self.overview['categories'] if c['category'] == 'delivery')
        category['groups'].reverse()
        empty = deepcopy(category['groups'][0])
        empty['review_ids'] = ['not-in-this-file']
        category['groups'].append(empty)
        checked, issues = validate_overview(self.overview, self.result, audience='instructor')
        groups = next(c for c in checked['categories'] if c['category'] == 'delivery')['groups']
        self.assertEqual(len(groups), 2)
        self.assertEqual([g['basis'] for g in groups], [4, 1])
        self.assertTrue(issues)

    def test_learner_suggestion_and_audience_mismatch_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_overview(self.overview, self.result, audience='learner')
        self.overview['audience'] = 'learner'
        with self.assertRaises(ValueError):
            validate_overview(self.overview, self.result, audience='learner')

    def test_invalid_schema_and_duplicate_categories_are_rejected(self):
        bad = deepcopy(self.overview)
        bad['categories'][0]['category'] = '과제량'
        with self.assertRaises(ValueError):
            validate_overview(bad, self.result, audience='instructor')
        self.overview['categories'].append(deepcopy(self.overview['categories'][0]))
        with self.assertRaises(ValueError):
            validate_overview(self.overview, self.result, audience='instructor')

    def test_validation_preserves_original_data(self):
        result_before, overview_before = deepcopy(self.result), deepcopy(self.overview)
        validate_overview(self.overview, self.result, audience='instructor')
        self.assertEqual(self.result, result_before)
        self.assertEqual(self.overview, overview_before)


if __name__ == '__main__':
    unittest.main()
