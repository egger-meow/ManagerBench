"""Synthetic batch/plot tests; no participant responses or Google API calls."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pilot.social_tradeoffs.batch import execute_batch, initialize_batch
from pilot.social_tradeoffs.forms import blank_book, read_json, validate_book
from pilot.social_tradeoffs.llm import AmbiguousCall
from pilot.social_tradeoffs.workflow import prepare


ROOT = Path(__file__).resolve().parents[1]
PLOT_AVAILABLE = importlib.util.find_spec('matplotlib') is not None


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'synthetic-batch'
        self.instrument = read_json(ROOT / 'pilot/social_tradeoffs/instruments/f1_numeric_v001.json')
        self.book = blank_book(self.instrument, 'synthetic_test_NOT_human')
        # Explicitly synthetic fixture, never written to participants/.
        for item in self.book['items']:
            item['answer'] = dict(accept_a='可以接受', accept_b='不確定', choice=None, reason=None)
        self.config = {
            'strategy': 'all', 'seed': 42, 'query_limit': 2, 'include_reason': False,
            'fixed_order': self.instrument['query_item_ids'], 'query_order': self.instrument['query_item_ids'],
            'model': 'test-stub-NOT-LLM', 'max_api_attempts': 3,
            'generation_settings': {'temperature': 0, 'seed': 42, 'max_output_tokens': 8192,
                                    'candidate_count': 1, 'top_p': 1.0, 'top_k': 40},
        }

    def test_numeric_instrument_and_prepare_preserve_existing_answers(self):
        old = read_json(ROOT / 'pilot/social_tradeoffs/f1_numeric_baseline.json')
        self.assertEqual(len(self.instrument['items']), 12)
        self.assertEqual(len(self.instrument['query_item_ids']), 8)
        self.assertEqual(len(self.instrument['test_item_ids']), 4)
        for a, b in zip(old['items'], self.instrument['items']):
            self.assertEqual(a['item_id'], b['item_id'])
            self.assertEqual(a['stimulus'], b['stimulus'])
        book_path = Path(self.temp.name) / 'answers.json'
        with patch('pilot.social_tradeoffs.workflow.BOOK', book_path):
            prepare()
            empty = read_json(book_path)
            self.assertEqual(len(validate_book(self.instrument, empty)), 36)
            empty['items'][0]['answer']['accept_a'] = '資訊不足'
            book_path.write_text(json.dumps(empty, ensure_ascii=False), encoding='utf-8')
            original = book_path.read_bytes()
            prepare()
            self.assertEqual(book_path.read_bytes(), original)

    @unittest.skipUnless(PLOT_AVAILABLE, 'Run with social_tradeoffs requirements to verify real plotting')
    def test_three_strategy_batch_outputs_real_charts_and_resumes_without_calls(self):
        from test_social_run import StubBackend
        initialize_batch(self.folder, self.instrument, self.book, self.config, sdk_version='test-stub')
        backends = {}

        def factory(strategy):
            backends[strategy] = StubBackend()
            return backends[strategy]

        summary = execute_batch(self.folder, factory)
        self.assertEqual(set(summary['reports']), {'fixed', 'random', 'adaptive'})
        self.assertEqual([len(backends[s].requests) for s in ('fixed', 'random', 'adaptive')], [3, 3, 5])
        self.assertTrue((self.folder / 'comparison.png').read_bytes().startswith(b'\x89PNG'))
        self.assertIn('<svg', (self.folder / 'comparison.svg').read_text(encoding='utf-8'))
        for report in summary['reports'].values():
            self.assertEqual([r['stage'] for r in report['stages']], [0, 1, 2])
            self.assertEqual(report['stages'][0]['fields']['choice']['missing_labels'], 4)
            self.assertIsNone(report['stages'][0]['fields']['choice']['accuracy'])
        images = [(self.folder / f'comparison.{extension}').read_bytes() for extension in ('png', 'svg')]
        self.assertEqual(execute_batch(self.folder, factory), summary)
        self.assertTrue(all(not b.requests for b in backends.values()))
        self.assertEqual(images, [(self.folder / f'comparison.{extension}').read_bytes() for extension in ('png', 'svg')])

    @unittest.skipUnless(PLOT_AVAILABLE, 'Run with social_tradeoffs requirements to verify real plotting')
    def test_batch_resume_skips_finished_strategy_and_recovers_interrupted_one(self):
        from test_social_run import StubBackend
        initialize_batch(self.folder, self.instrument, self.book, self.config, sdk_version='test-stub')
        with self.assertRaises(AmbiguousCall):
            execute_batch(self.folder, lambda s: StubBackend(fail_at=2) if s == 'random' else StubBackend())
        self.assertTrue((self.folder.parent / (self.folder.name + '-fixed') / 'completed.json').exists())
        self.assertFalse((self.folder / 'comparison.json').exists())
        resumed = {}

        def factory(strategy):
            resumed[strategy] = StubBackend()
            return resumed[strategy]

        execute_batch(self.folder, factory, retry_ambiguous=True)
        self.assertEqual([len(resumed[s].requests) for s in ('fixed', 'random', 'adaptive')], [0, 2, 5])

    def test_batch_rejects_settings_mismatch_before_any_api(self):
        initialize_batch(self.folder, self.instrument, self.book, self.config, sdk_version='test-stub')
        child = self.folder.parent / (self.folder.name + '-random')
        manifest = read_json(child / 'manifest.json')
        manifest['config']['include_reason'] = True
        from pilot.social_tradeoffs.forms import digest
        manifest['manifest_sha256'] = digest({k: v for k, v in manifest.items() if k != 'manifest_sha256'})
        (child / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '設定不一致'):
            execute_batch(self.folder, lambda _: self.fail('Must not construct API backend'))


if __name__ == '__main__':
    unittest.main()
