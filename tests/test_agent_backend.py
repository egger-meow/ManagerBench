import json
from pathlib import Path
import tempfile
import unittest

from pilot.social_tradeoffs.agent_backend import AgentBackend, format_agent_prompt, strip_markdown_fences


class TestAgentBackend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_strip_markdown_fences(self):
        wrapped = "```json\n{\"key\": \"val\"}\n```"
        self.assertEqual(strip_markdown_fences(wrapped), '{"key": "val"}')
        raw = "{\"key\": \"val\"}"
        self.assertEqual(strip_markdown_fences(raw), raw)

    def test_format_agent_prompt(self):
        request = {
            'model': 'gemini-3.8-flash',
            'role': 'predictor',
            'prompt': '預測測試指示',
            'payload': {'targets': [{'item_id': 'test-01'}]},
            'response_schema': {'type': 'object', 'properties': {'test-01': {'type': 'string'}}},
        }
        prompt = format_agent_prompt(request)
        self.assertIn('gemini-3.8-flash', prompt)
        self.assertIn('預測測試指示', prompt)
        self.assertIn('test-01', prompt)
        self.assertIn('[輸出格式要求 (JSON Schema)]', prompt)

    def test_generate_via_outbox_file(self):
        backend = AgentBackend(inbox_path=self.folder / 'agent_inbox.md',
                               outbox_path=self.folder / 'agent_outbox.json',
                               interactive=False)
        request = {
            'model': 'gemini-3.8-flash',
            'role': 'selector',
            'prompt': '選題測試',
            'payload': {'targets': [{'item_id': 'q1'}]},
            'response_schema': {'type': 'object'},
        }
        expected_output = {'item_id': 'q1'}
        # Pre-seed outbox file
        (self.folder / 'agent_outbox.json').write_text(json.dumps(expected_output), encoding='utf-8')

        result = backend.generate(request, clean_outbox=False)
        self.assertEqual(json.loads(result['text']), expected_output)
        self.assertEqual(result['raw']['origin'], 'agent_interactive')
        self.assertEqual(result['model_version'], 'agent-mimic:gemini-3.8-flash')
        self.assertTrue((self.folder / 'agent_inbox.md').exists())


if __name__ == '__main__':
    unittest.main()
