"""Offline synthetic fixtures and API stubs; not human/LLM experiment results."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pilot.social_tradeoffs.forms import blank_book, instrument_hash, read_json
from pilot.social_tradeoffs.llm import AmbiguousCall, JournalClient, usage_report
from pilot.social_tradeoffs.run import execute, initialize, load_run, validate_config
from pilot.social_tradeoffs.storage import run_lock
from pilot.social_tradeoffs.strategies import choose


ROOT = Path(__file__).resolve().parents[1]


class StubBackend:
    """Explicit API stub, never calls Google and never reads an answer book."""
    def __init__(self, fail_at=None, invalid_at=None):
        self.requests = []
        self.fail_at = fail_at
        self.invalid_at = invalid_at

    def generate(self, request):
        self.requests.append(copy.deepcopy(request))
        index = len(self.requests)
        if index == self.fail_at:
            raise TimeoutError('TEST_SECRET_MUST_NOT_APPEAR_IN_LOGS')
        if request['role'] == 'selector':
            value = {'item_id': request['payload']['targets'][0]['item_id']}
        else:
            value = {item['item_id']: {
                'accept_a': '可以接受', 'accept_b': '不確定', 'choice': None,
            } for item in request['payload']['targets']}
        text = 'invalid test output' if index == self.invalid_at else json.dumps(value, ensure_ascii=False)
        return {'text': text, 'raw': {'origin': 'offline_unit_test_stub', 'text': text},
                'usage': {'prompt_token_count': 5, 'candidates_token_count': 2},
                'model_version': 'test-stub-NOT-LLM'}


class SocialRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'test-run'
        self.instrument = read_json(ROOT / 'pilot/social_tradeoffs/instruments/f1_context_v001.json')
        # Test-only split. Does NOT create/change any public research instrument.
        self.instrument['instrument_id'] = 'test_fixture_v001'
        self.instrument['version'] = 'fixture-001'
        self.test_id = self.instrument['query_item_ids'].pop()
        self.instrument['test_item_ids'] = [self.test_id]
        self.instrument['status'] = 'synthetic_unit_test_fixture_NOT_research_split'
        self.instrument['content_sha256'] = instrument_hash(self.instrument)
        self.book = blank_book(self.instrument, 'synthetic_test_NOT_human')
        for item in self.book['items']:
            item['answer'] = dict(accept_a='可以接受', accept_b='不確定',
                                  choice='拒絕作此決策', reason='QUERY_REASON_SENTINEL')
            if item['item_id'] == self.test_id:
                item['answer']['reason'] = 'TEST_REASON_SENTINEL'
        self.config = {
            'strategy': 'fixed', 'seed': 42, 'query_limit': 2, 'include_reason': False,
            'fixed_order': self.instrument['query_item_ids'],
            'query_order': self.instrument['query_item_ids'],
            'model': 'test-stub-NOT-LLM', 'max_api_attempts': 3,
            'generation_settings': {'temperature': 0, 'seed': 42, 'max_output_tokens': 8192,
                                    'candidate_count': 1, 'top_p': 1.0, 'top_k': 40},
        }

    def start(self):
        initialize(self.folder, self.instrument, self.book, self.config, sdk_version='unit-test-no-sdk')

    def test_each_strategy_baseline_boundary_scoring_and_completed_resume(self):
        predictor_payloads = []
        for strategy in ('fixed', 'random', 'adaptive'):
            self.folder = Path(self.temp.name) / strategy
            self.config['strategy'] = strategy
            self.start()
            backend = StubBackend()
            scores = execute(self.folder, backend)
            predictions = [r for r in backend.requests if r['role'] == 'predictor']
            self.assertEqual([len(r['payload']['revealed_queries']) for r in predictions], [0, 1, 2])
            predictor_payloads.append(predictions[0]['payload'])
            for request in backend.requests:
                text = json.dumps(request['payload'])
                for forbidden in ('TEST_REASON_SENTINEL', 'QUERY_REASON_SENTINEL',
                                  'research_notes', 'possible_reasons', 'provenance', 'parameters'):
                    self.assertNotIn(forbidden, text)
                if request['role'] == 'selector':
                    self.assertNotIn(self.test_id, text)
                    self.assertNotIn('predictions', text)
                for target in request['payload']['targets']:
                    self.assertNotIn('answer', target)
            self.assertEqual(scores['stages'][0]['fields']['accept_a']['accuracy'], 1.0)
            self.assertEqual(scores['stages'][0]['fields']['choice']['coverage'], 0.0)
            self.assertIsNone(scores['stages'][0]['fields']['choice']['accuracy'])
            self.assertEqual(len(read_json(self.folder / 'manifest.json')['config']['query_order']), 6)
            events = [json.loads(line) for line in (self.folder / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len({e['query_item_id'] for e in events}), 2)
            unused = StubBackend()
            self.assertEqual(execute(self.folder, unused), scores)
            self.assertEqual(unused.requests, [])
        self.assertEqual(predictor_payloads[0], predictor_payloads[1])
        self.assertEqual(predictor_payloads[1], predictor_payloads[2])

    def test_ambiguous_call_blocks_default_resume_then_reuses_completed_calls(self):
        self.start()
        backend = StubBackend(fail_at=2)
        with self.assertRaises(AmbiguousCall):
            execute(self.folder, backend)
        self.assertTrue((self.folder / 'predictions/stage-0000.json').exists())
        self.assertFalse((self.folder / 'scores.json').exists())
        unused = StubBackend()
        with self.assertRaises(AmbiguousCall):
            execute(self.folder, unused)
        self.assertEqual(unused.requests, [])
        resumed = StubBackend()
        execute(self.folder, resumed, retry_ambiguous=True)
        self.assertEqual(len(resumed.requests), 2)  # only k=1 and k=2; k=0 reused
        log = read_json(self.folder / 'api/predict-0001/attempt-01/error.json')
        self.assertNotIn('TEST_SECRET', str(log))
        self.assertEqual(log['kind'], 'ambiguous')
        self.assertEqual(len(usage_report(self.folder)['unknown_usage_attempts']), 1)

    def test_saved_raw_response_recovers_without_another_request(self):
        self.config['query_limit'] = 0
        self.start()
        backend = StubBackend(invalid_at=1)
        execute(self.folder, backend)
        self.assertEqual(len(backend.requests), 2)
        self.assertTrue((self.folder / 'api/predict-0000/attempt-01/invalid.json').exists())
        self.assertEqual(usage_report(self.folder)['completed_responses'], 2)
        # Simulate crash after raw response persistence but before validated cache.
        (self.folder / 'api/predict-0000/validated.json').unlink()
        manifest, _, _, prompts = load_run(self.folder)
        unused = StubBackend()
        client = JournalClient(self.folder, manifest['config'], prompts, unused)
        request = read_json(self.folder / 'api/predict-0000/request.json')
        from pilot.social_tradeoffs.predictor import contract
        schema, validate = contract(request['payload']['targets'])
        client.call('predict-0000', 'predictor', request['payload'], schema, validate)
        self.assertEqual(unused.requests, [])

    def test_interrupt_after_api_response_before_stage_checkpoint_resumes_without_repayment(self):
        self.start()
        backend = StubBackend()
        from pilot.social_tradeoffs import run
        original_save = run.save

        def interrupt(path, value):
            if str(path).endswith('stage-0001.json'):
                raise KeyboardInterrupt('offline test interrupt')
            return original_save(path, value)

        with patch.object(run, 'save', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                execute(self.folder, backend)
        self.assertEqual(len(backend.requests), 2)
        self.assertTrue((self.folder / 'api/predict-0001/validated.json').exists())
        self.assertFalse((self.folder / 'predictions/stage-0001.json').exists())
        resumed = StubBackend()
        execute(self.folder, resumed)
        self.assertEqual(len(resumed.requests), 1)  # only the not-yet-called k=2
        self.assertEqual(len(resumed.requests[0]['payload']['revealed_queries']), 2)

    def test_reason_explicit_partial_answers_and_missing_labels(self):
        self.config['include_reason'] = True
        self.config['strategy'] = 'adaptive'
        self.book['items'][0]['answer']['accept_a'] = None
        self.book['items'][-1]['answer']['accept_b'] = None
        self.start()
        backend = StubBackend()
        scores = execute(self.folder, backend)
        self.assertEqual(scores['stages'][0]['fields']['accept_b']['missing_labels'], 1)
        self.assertIsNone(scores['stages'][0]['fields']['accept_b']['accuracy'])
        history = backend.requests[2]['payload']['revealed_queries']
        self.assertEqual(history[0]['answer']['reason'], 'QUERY_REASON_SENTINEL')
        self.assertIsNone(history[0]['answer']['accept_a'])
        self.assertNotIn('TEST_REASON_SENTINEL', str(backend.requests))

    def test_preflight_rejects_empty_test_pool_blank_test_and_invalid_fixed_order(self):
        public = read_json(ROOT / 'pilot/social_tradeoffs/instruments/f1_context_v001.json')
        with self.assertRaisesRegex(ValueError, 'test ID'):
            validate_config(public, blank_book(public, 'test'), self.config)
        for field in ('accept_a', 'accept_b', 'choice'):
            self.book['items'][-1]['answer'][field] = None
        with self.assertRaisesRegex(ValueError, '完全未回答'):
            self.start()
        self.assertFalse(self.folder.exists())
        self.book['items'][-1]['answer']['accept_a'] = '資訊不足'
        self.config['fixed_order'] = [self.test_id]
        with self.assertRaisesRegex(ValueError, 'fixed_order'):
            self.start()

    def test_snapshot_mutation_overwrite_and_concurrent_resume_rejected(self):
        self.start()
        with self.assertRaises(FileExistsError):
            self.start()
        with run_lock(self.folder):
            with self.assertRaises(ValueError):
                execute(self.folder, StubBackend())
        snapshot = read_json(self.folder / 'answers.snapshot.json')
        snapshot['items'][0]['answer']['reason'] = 'changed'
        (self.folder / 'answers.snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
        backend = StubBackend()
        with self.assertRaisesRegex(ValueError, '雜湊'):
            execute(self.folder, backend)
        self.assertEqual(backend.requests, [])

    def test_random_selector_is_stable_without_replacement_across_resume(self):
        from pilot.social_tradeoffs.forms import model_payload
        history = {}
        selected = []
        for stage in range(6):
            remaining = [i for i in self.instrument['query_item_ids'] if i not in history]
            payload = model_payload(self.instrument, history, remaining)
            item = choose('random', payload, self.config, stage, None)
            self.assertEqual(item, choose('random', payload, self.config, stage, None))
            selected.append(item)
            history[item] = dict.fromkeys(('accept_a', 'accept_b', 'choice', 'reason'))
        self.assertEqual(len(set(selected)), 6)


if __name__ == '__main__':
    unittest.main()
