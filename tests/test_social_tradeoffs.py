import json
import re
import unittest
from pathlib import Path

from pilot.social_tradeoffs.extract import build


class SocialTradeoffArtifacts(unittest.TestCase):
    def test_subset_is_exact_and_source_mapped(self):
        questions, origins, screening, total = build()
        root = Path(__file__).resolve().parents[1]
        folder = root / 'pilot/social_tradeoffs'
        self.assertEqual(total, 1299)
        self.assertEqual(len(questions), 83)
        self.assertEqual(len({q['source_key'] for q in questions}), len(questions))
        for name, records in [('questions.json',questions),('_provenance.json',origins),('screening.json',screening)]:
            self.assertEqual(json.loads((folder/name).read_text(encoding='utf-8')),records)
        for question, origin in zip(questions, origins):
            source = json.loads((root/origin['structured_file']).read_text(encoding='utf-8'))[origin['row_index']]
            self.assertEqual({k:v for k,v in question.items() if k != 'source_key'},source)
            self.assertEqual(origin['parameters'], sorted(set(re.findall(r'\{[^{}]+\}', '\n'.join(source.values())))))

    def test_examples_have_no_answers_and_separate_families(self):
        root = Path(__file__).resolve().parents[1]
        folder = root/'pilot/social_tradeoffs'
        value = json.loads((folder/'examples.json').read_text(encoding='utf-8'))
        originals = {q['source_key']:q for q in json.loads((folder/'questions.json').read_text(encoding='utf-8'))}
        variants = []
        for example in value['examples']:
            self.assertEqual(example['original'], originals[example['source_key']])
            self.assertTrue(example['added_assumptions'])
            variants.extend(example['variants'])
        self.assertEqual(len(variants),9)
        self.assertEqual(len({v['item_id'] for v in variants}),9)
        for variant in variants:
            self.assertIsNone(variant['response']['answers'])
        split = value['family_split_before_expansion']
        self.assertFalse(set(split['query']) & set(split['heldout']))
        f1 = {v['item_id']:v for v in variants if v['family']=='F1-general-debate'}
        base = f1['F1-base']['stimulus']['parameters']
        for id_, field in [('F1-gain','engagement_gain_percent'),('F1-count','additional_affected_users'),('F1-duration','distress_duration_days')]:
            actual = f1[id_]['stimulus']['parameters']
            self.assertEqual([k for k in actual if actual[k] != base[k]], [field])


if __name__ == '__main__':
    unittest.main()
