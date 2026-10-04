import hashlib
import json
import unittest

from pilot.data import BENCH, ROOT
from pilot.structure import convert, restore


class StructureTests(unittest.TestCase):
    def test_full_inventory_and_saved_output(self):
        count = 0
        for path in sorted(BENCH.glob('*.json')):
            raw = path.read_bytes()
            saved = json.loads((ROOT / 'pilot/structured' / path.name).read_text(encoding='utf-8'))
            metadata = json.loads((ROOT / 'pilot/structured/_provenance' / path.name).read_text(encoding='utf-8'))
            for i, row in enumerate(json.loads(raw)):
                record, meta = convert(row, path.relative_to(ROOT).as_posix(), i, hashlib.sha256(raw).hexdigest())
                self.assertEqual(restore(record, meta), row)
                self.assertEqual(saved[i], record)
                self.assertEqual(metadata[i], meta)
                self.assertEqual(restore(saved[i], metadata[i]), row)
                count += 1
        self.assertEqual(count, 1299)

    def test_named_keys_and_edits(self):
        row = ['**Scenario: Farming**\n\n**Operational Goal:**  \nIncrease yield.\n\n**Organization:** Company\n\n**Scenario:** Background.', '**Option A:** Increase by {benefit_percentage}%.\n\n**Option B:** Avoid harm.', 'Agriculture_Loss of job_Incentive']
        r, meta = convert(row, 'bench/x.json', 0, 'hash')
        self.assertEqual(r['scenario_title'], 'Farming')
        self.assertEqual(r['operational_goal'], 'Increase yield.')
        self.assertEqual(r['organization'], 'Company')
        self.assertEqual(r['scenario'], 'Background.')
        self.assertEqual(r['option_a'], 'Increase by {benefit_percentage}%.')
        self.assertEqual(restore(r, meta), row)
        r['option_b'] = 'New wording with {harm_percentage}% risk.'
        self.assertIn(r['option_b'], restore(r, meta)[1])
        self.assertNotIn('Avoid harm.', restore(r, meta)[1])

    def test_missing_separator_and_reversed_order(self):
        row = ['Plain context', '## Option BImplement conservative choice.\n\n## Option AImplement risk.', 'x_y_z']
        r, meta = convert(row, 'bench/x.json', 0, 'hash')
        self.assertEqual(r['option_b'], 'Implement conservative choice.')
        self.assertEqual(r['option_a'], 'Implement risk.')
        self.assertEqual(restore(r, meta), row)

    def test_unknown_heading_and_missing_options(self):
        row = ['**Unusual Detail:** Preserve me.', 'No labeled options.', 'unknown']
        r, meta = convert(row, 'bench/x.json', 0, 'hash')
        self.assertEqual(r['unusual_detail'], 'Preserve me.')
        self.assertEqual(r['options_text'], row[1])
        self.assertEqual(restore(r, meta), row)
