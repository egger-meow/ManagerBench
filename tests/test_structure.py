import hashlib
import json
import unittest

from pilot.data import BENCH, ROOT
from pilot.structure import convert, meaning


class StructureTests(unittest.TestCase):
    def test_full_inventory_lossless(self):
        count = 0
        for path in sorted(BENCH.glob('*.json')):
            raw = path.read_bytes()
            for i, row in enumerate(json.loads(raw)):
                r = convert(row, path.relative_to(ROOT).as_posix(), i, hashlib.sha256(raw).hexdigest())
                self.assertEqual(r['raw'], row)
                fields = {'scenario': row[0], 'alternatives': row[1]}
                spans = r['scenario_sections'] + [p['source'] for p in r['parameters']]
                if r['options']:
                    self.assertEqual(r['option_preamble']['text'] + ''.join(o['source']['text'] for o in r['options']), row[1])
                for o in r['options']:
                    self.assertEqual(''.join(s['source']['text'] for s in o['segments']), o['body']['text'])
                    spans.extend([o['source'], o['body']])
                    spans.extend(s['source'] for s in o['segments'])
                for s in spans:
                    self.assertEqual(s['text'], fields[s['field']][s['start']:s['end']])
                count += 1
        self.assertEqual(count, 1299)

    def test_semantics_and_reversed_roles(self):
        row = ['Plain context', 'Option A: No gain.\nOption B: A {harm_percentage}% chance of illness.', 'x_y_z']
        r = convert(row, 'bench/x.json', 0, 'hash')
        self.assertEqual(r['parameters'][0]['option'], 'B')
        self.assertEqual(r['parameters'][0]['meaning']['candidates'], ['event_probability'])
        self.assertIsNone(r['parameters'][0]['value'])
        for phrase, expected in [('risk', 'event_probability'), ('of current farm workers', 'affected_population_share'), ('of operations', 'case_frequency'), ('of units', 'affected_object_share')]:
            text = '{harm_percentage}% ' + phrase
            self.assertIn(expected, meaning(text, 0, len('{harm_percentage}')))

    def test_failures_preserve_source(self):
        for row in [['bad'], ['context', 'choose something', 'key']]:
            r = convert(row, 'bench/x.json', 0, 'hash')
            self.assertEqual(r['raw'], row)
            self.assertTrue(r['issues'])

    def test_ambiguous_parameter(self):
        r = convert(['context', 'Option A: {harm_percentage}% unspecified.\nOption B: Nothing.', 'x_y_z'], 'bench/x.json', 0, 'hash')
        self.assertEqual(r['parameters'][0]['meaning']['status'], 'ambiguous_or_missing')


if __name__ == '__main__':
    unittest.main()
