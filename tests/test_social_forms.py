import copy
import unittest
from pathlib import Path

from pilot.social_tradeoffs.forms import (
    blank_book, digest, instrument_hash, model_payload, read_json, validate_book,
    validate_instrument,
)


class SocialForms(unittest.TestCase):
    def setUp(self):
        self.instrument = read_json(Path(__file__).resolve().parents[1] /
                                    'pilot/social_tradeoffs/instruments/f1_context_v001.json')

    def test_partial_answers_and_tampering(self):
        book = blank_book(self.instrument, 'p001')
        self.assertEqual(len(validate_book(self.instrument, book)), 21)
        book['items'][0]['answer']['accept_a'] = '資訊不足'
        self.assertEqual(len(validate_book(self.instrument, book)), 20)
        for mutate in (
            lambda b: b['items'][0]['answer'].update(choice='A'),
            lambda b: b.update(instrument_version='002'),
            lambda b: b['items'][0]['stimulus'].update(scenario='changed'),
            lambda b: b['items'].append(copy.deepcopy(b['items'][0])),
        ):
            changed = copy.deepcopy(book)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_book(self.instrument, changed)

    def test_public_instrument_and_split(self):
        validate_instrument(self.instrument)
        self.assertEqual(self.instrument['test_item_ids'], [])
        changed = copy.deepcopy(self.instrument)
        changed['items'][0]['response']['answers'] = {'choice': 'A'}
        changed['content_sha256'] = instrument_hash(changed)
        with self.assertRaises(ValueError):
            validate_instrument(changed)
        changed = copy.deepcopy(self.instrument)
        changed['test_item_ids'] = changed['query_item_ids'][:1]
        changed['content_sha256'] = instrument_hash(changed)
        with self.assertRaises(ValueError):
            validate_instrument(changed)

    def test_boundary_rejects_test_answers_and_strips_reason_metadata(self):
        # Synthetic split fixture for boundary testing, not a research test set.
        instrument = copy.deepcopy(self.instrument)
        test_id = instrument['query_item_ids'].pop()
        instrument['test_item_ids'] = [test_id]
        instrument['content_sha256'] = instrument_hash(instrument)
        query_id = instrument['query_item_ids'][0]
        answer = dict(accept_a='不確定', accept_b=None, choice=None, reason='PRIVATE_REASON')
        payload = model_payload(instrument, {query_id: answer}, [test_id])
        text = str(payload)
        for forbidden in ('PRIVATE_REASON', 'research_notes', 'provenance', 'parameters', 'test_item_ids', 'possible_reasons'):
            self.assertNotIn(forbidden, text)
        self.assertNotIn('answer', payload['targets'][0])
        self.assertIn('PRIVATE_REASON', str(model_payload(instrument, {query_id: answer}, [test_id], include_reason=True)))
        with self.assertRaises(ValueError):
            model_payload(instrument, {test_id: answer}, [query_id])
        self.assertEqual(digest({'a': 1, 'b': 2}), digest({'b': 2, 'a': 1}))


if __name__ == '__main__':
    unittest.main()
