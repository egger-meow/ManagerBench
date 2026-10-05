import json
import itertools
import re
import unittest
from pathlib import Path

from pilot.social_tradeoffs.extract import build


class SocialTradeoffArtifacts(unittest.TestCase):
    def test_f1_pool_is_complete_and_preserves_confirmed_template(self):
        folder = Path(__file__).resolve().parents[1] / 'pilot/social_tradeoffs'
        pool = json.loads((folder / 'f1_question_pool.json').read_text(encoding='utf-8'))
        example = json.loads((folder / 'examples.json').read_text(encoding='utf-8'))['examples'][0]
        base = example['variants'][0]
        items = pool['items']
        expected = set(itertools.product((5, 15), (100, 300, 500), (1, 3)))
        self.assertEqual(len(items), 12)
        self.assertEqual(len({item['item_id'] for item in items}), 12)
        actual = set()
        matched_examples = {}
        for item in items:
            stimulus = item['stimulus']
            p = stimulus['parameters']
            gain, count, days = (p['engagement_gain_percent'],
                                 p['additional_affected_users'], p['distress_duration_days'])
            actual.add((gain, count, days))
            self.assertEqual(item['item_id'], f'F1-g{gain}-n{count}-d{days}')
            self.assertEqual(item['family'], 'F1-general-debate')
            self.assertEqual(item['source_key'], example['source_key'])
            self.assertEqual(item['provenance']['original_source_key'], example['source_key'])
            self.assertEqual(item['provenance']['template_item_id'], 'F1-base')
            self.assertEqual(p['population'], 10000)
            self.assertEqual(p['additional_affected_users_percent'], count * 100 / p['population'])
            self.assertEqual(p['baseline_weekly_interactions'], 100000)
            self.assertEqual(p['option_a_weekly_interactions'], 100000 * (100 + gain) // 100)
            self.assertEqual(p['option_b_weekly_interactions'], 100000)
            for key, value in base['stimulus'].items():
                if key not in ('parameters', 'option_a'):
                    self.assertEqual(stimulus[key], value.replace('判断', '判斷'))
            expected_a = (base['stimulus']['option_a']
                          .replace('增加 5%', f'增加 {gain}%')
                          .replace('105,000', f'{p["option_a_weekly_interactions"]:,}')
                          .replace('新增 100 人（1%）', f'新增 {count} 人（{count // 100}%）')
                          .replace('持續 1 日', f'持續 {days} 日')
                          .replace('人数', '人數'))
            self.assertEqual(stimulus['option_a'], expected_a)
            response = item['response']
            for key, value in base['response'].items():
                self.assertEqual(response[key], value)
            self.assertEqual(set(response['accept_a_and_b_labels_zh_tw']), set(response['accept_a_and_b_values']))
            self.assertEqual(set(response['choice_labels_zh_tw']), set(response['choice_values']))
            self.assertEqual(response['answer_format']['fields'],
                             dict.fromkeys(('accept_a', 'accept_b', 'choice', 'reason')))
            matching = item['provenance']['matching_example_item_id']
            if matching is not None:
                matched_examples[matching] = (gain, count, days)
        self.assertEqual(actual, expected)
        self.assertEqual(matched_examples, {
            v['item_id']: (v['stimulus']['parameters']['engagement_gain_percent'],
                           v['stimulus']['parameters']['additional_affected_users'],
                           v['stimulus']['parameters']['distress_duration_days'])
            for v in example['variants']
        })

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
