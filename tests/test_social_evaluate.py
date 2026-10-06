"""Scoring fixtures only; no human responses or model calls."""
import unittest

from pilot.social_tradeoffs.evaluate import score


class SocialEvaluationTests(unittest.TestCase):
    def report(self, labels, predictions):
        instrument = {'test_item_ids': [str(i) for i in range(len(labels))]}
        book = {'items': [{'item_id': str(i), 'answer': dict.fromkeys(
            ('accept_a', 'accept_b', 'choice'), label)} for i, label in enumerate(labels)]}
        guesses = {str(i): dict.fromkeys(('accept_a', 'accept_b', 'choice'), value)
                   for i, value in enumerate(predictions)}
        return score(instrument, book, [(0, guesses)])

    def test_one_correct_three_abstentions_is_quarter_primary_not_perfect(self):
        report = self.report(['可以接受'] * 4, ['可以接受', None, None, None])
        self.assertEqual(report['primary_metric'], 'accuracy_all_answered')
        self.assertEqual(report['scoring_version'], 'social-exact-v2')
        for field in report['stages'][0]['fields'].values():
            self.assertEqual(field['accuracy_all_answered'], 0.25)
            self.assertEqual(field['accuracy'], 1)
            self.assertEqual(field['coverage'], 0.25)

    def test_missing_human_labels_excluded_but_valid_uncertainty_is_scored(self):
        report = self.report(['不確定', '資訊不足', '拒絕作此決策', None],
                             ['不確定', '可以接受', None, '可以接受'])
        for field in report['stages'][0]['fields'].values():
            self.assertEqual(field['accuracy_all_answered'], 1 / 3)
            self.assertEqual(field['accuracy'], 1 / 2)
            self.assertEqual(field['coverage'], 2 / 3)
            self.assertEqual(field['missing_labels'], 1)
        for field in self.report(['可以接受'], [None])['stages'][0]['fields'].values():
            self.assertEqual(field['accuracy_all_answered'], 0)
            self.assertIsNone(field['accuracy'])
        for field in self.report([None], ['可以接受'])['stages'][0]['fields'].values():
            self.assertIsNone(field['accuracy_all_answered'])
            self.assertIsNone(field['accuracy'])
            self.assertIsNone(field['coverage'])
