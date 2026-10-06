import json
import itertools
import re
import unittest
from pathlib import Path

from pilot.social_tradeoffs.extract import build
from pilot.provenance import verify_source_hash


class SocialTradeoffArtifacts(unittest.TestCase):
    def test_f1_numeric_baseline_is_complete_and_preserves_confirmed_template(self):
        folder = Path(__file__).resolve().parents[1] / 'pilot/social_tradeoffs'
        pool = json.loads((folder / 'f1_numeric_baseline.json').read_text(encoding='utf-8'))
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

    def test_context_pool_preserves_pairs_units_and_empty_responses(self):
        folder = Path(__file__).resolve().parents[1] / 'pilot/social_tradeoffs'
        pool = json.loads((folder / 'f1_question_pool.json').read_text(encoding='utf-8'))
        baseline = json.loads((folder / 'f1_numeric_baseline.json').read_text(encoding='utf-8'))
        items = {item['item_id']: item for item in pool['items']}
        self.assertEqual(len(items), 7)
        self.assertEqual(len(pool['items']), 7)
        self.assertEqual(len(pool['pairs']), 4)
        self.assertFalse(set(items) & {item['item_id'] for item in baseline['items']})
        referenced = set()
        for pair in pool['pairs']:
            left, right = [items[id_] for id_ in pair['item_ids']]
            referenced.update(pair['item_ids'])
            self.assertTrue(pair['possible_reasons'])
            self.assertTrue(pair['confounds'])
            lp, rp = left['stimulus']['parameters'], right['stimulus']['parameters']
            self.assertEqual(set(lp), set(rp))
            self.assertEqual({key for key in lp if lp[key] != rp[key]}, set(pair['parameter_changes']))
            self.assertEqual({key for key in left['stimulus'] if key != 'parameters'
                              and left['stimulus'][key] != right['stimulus'][key]},
                             set(pair['stimulus_changes']))
            self.assertEqual(left['response'], right['response'])
        self.assertEqual(referenced, set(items))
        for item in items.values():
            s = item['stimulus']
            p = s['parameters']
            self.assertEqual(item['family'], 'F1-general-debate')
            self.assertEqual(item['source_key'], 'chatgpt_results:264')
            self.assertEqual(item['provenance']['original_source_key'], item['source_key'])
            self.assertTrue(item['provenance']['added_assumptions'])
            self.assertEqual(item['response'], baseline['items'][0]['response'])
            self.assertEqual(p['population'], 10000)
            self.assertEqual(p['additional_exposure_users'], 1000)
            self.assertLessEqual(p['additional_affected_users'], p['additional_exposure_users'])
            self.assertEqual(p['additional_affected_users_percent'], p['additional_affected_users'] / 100)
            self.assertEqual(p['distress_events'], p['additional_affected_users'] * p['events_per_affected_user'])
            self.assertEqual(p['distress_duration_unit'], 'days_per_event')
            self.assertEqual(p['total_distress_days_per_affected_user'],
                             p['events_per_affected_user'] * p['distress_duration_days'])
            self.assertEqual(p['baseline_weekly_interactions'], 100000)
            self.assertEqual(p['option_b_weekly_interactions'], 100000)
            self.assertEqual(p['option_a_weekly_interactions'], 100000 + 1000 * p['engagement_gain_percent'])
            self.assertIn(f"增加 {p['engagement_gain_percent']}%", s['option_a'])
            self.assertIn(f"{p['option_a_weekly_interactions']:,} 次", s['option_a'])
            self.assertIn(f"新增 {p['additional_affected_users']} 名不同", s['option_a'])
            self.assertIn(f"共 {p['distress_events']} 次困擾事件", s['option_a'])
            self.assertIn('每次持續 1 日', s['option_a'])
            self.assertIn('各題是彼此獨立', s['scenario'])
            self.assertNotIn('可能理由', s['option_a'])
        spread = items['F1-context-burden-spread']['stimulus']['parameters']
        repeat = items['F1-context-burden-repeat']['stimulus']['parameters']
        self.assertEqual((spread['additional_affected_users'], spread['distress_events'], spread['events_per_affected_user']), (300, 300, 1))
        self.assertEqual((repeat['additional_affected_users'], repeat['distress_events'], repeat['events_per_affected_user']), (100, 300, 3))
        self.assertIn('並非連續三日', items['F1-context-burden-repeat']['stimulus']['option_a'])

    def test_subset_is_exact_and_source_mapped(self):
        questions, origins, screening, total = build()
        root = Path(__file__).resolve().parents[1]
        folder = root / 'pilot/social_tradeoffs'
        self.assertEqual(total, 1299)
        self.assertEqual(len(questions), 83)
        self.assertEqual(len({q['source_key'] for q in questions}), len(questions))
        for name, records in [('questions.json',questions),('_provenance.json',origins),('screening.json',screening)]:
            saved = json.loads((folder/name).read_text(encoding='utf-8'))
            if name == '_provenance.json':
                self.assertEqual(len(saved), len(records))
                for historical, current in zip(saved, records):
                    # Export still records current raw bytes; compare historical hashes
                    # only after proving the checkout differs solely in line endings.
                    raw = (root/current['structured_file']).read_bytes()
                    verified = verify_source_hash(raw, historical['structured_sha256'])
                    self.assertEqual(current['structured_sha256'], verified['actual_sha256'])
                    current = {**current, 'structured_sha256': historical['structured_sha256']}
                    self.assertEqual(historical, current)
            else:
                self.assertEqual(saved, records)
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
