"""Offline coordinator checks; no real agent or participant data is used."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from pilot.social_tradeoffs.agent_pair import CodexAgentBackend, codex_command, validate_trace
from pilot.social_tradeoffs.llm import AmbiguousCall, JournalClient


class AgentPairTests(unittest.TestCase):
    def test_fresh_agent_command_disables_context_sources(self):
        command = codex_command('codex.cmd', 'test-model', Path('empty'), Path('final.json'))
        for flag in ('--ignore-user-config', '--ephemeral', '--sandbox', '--json'):
            self.assertIn(flag, command)
        for feature in ('memories', 'plugins', 'apps', 'multi_agent', 'shell_tool'):
            self.assertIn(['--disable', feature], [command[i:i+2] for i in range(len(command)-1)])
        for config in ('project_doc_max_bytes=0', 'memories.use_memories=false',
                       'memories.generate_memories=false', 'web_search=disabled'):
            self.assertIn(config, command)
        self.assertEqual(command[-1], '-')
        self.assertNotIn('resume', command)
        self.assertEqual(command[command.index('--model') + 1], 'test-model')

    def test_completed_message_is_accepted(self):
        validate_trace('\n'.join(json.dumps(e) for e in [
            {'type': 'thread.started'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{}'}},
            {'type': 'turn.completed'}]))

    def test_tool_activity_is_rejected(self):
        for kind in ('command_execution', 'mcp_tool_call', 'web_search', 'file_change'):
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                validate_trace(json.dumps({'type': 'item.completed', 'item': {'type': kind}}))

    def test_incomplete_or_failed_turn_is_rejected(self):
        for event in ({'type': 'thread.started'}, {'type': 'turn.failed'}, {'type': 'error'}):
            with self.subTest(event=event), self.assertRaises(RuntimeError):
                validate_trace(json.dumps(event))

    def test_automatic_failure_cannot_open_recovery_or_switch_to_google(self):
        class AutomaticFailureBackend:
            allow_interactive_recovery = False

            def generate(self, request):
                raise RuntimeError('Synthetic transport failure for offline test')

        with tempfile.TemporaryDirectory() as directory:
            client = JournalClient(Path(directory),
                                   {'model': 'test-model', 'generation_settings': {}, 'max_api_attempts': 1},
                                   {'predictor': 'Offline synthetic test'}, AutomaticFailureBackend())
            with patch('pilot.social_tradeoffs.llm.handle_interactive_error',
                       side_effect=AssertionError('Must not open interactive recovery')), \
                 patch('pilot.social_tradeoffs.llm.GoogleBackend',
                       side_effect=AssertionError('Must not construct Google client')):
                with self.assertRaises(AmbiguousCall):
                    client.call('test-call', 'predictor', {}, {}, lambda value: None)

    def test_transport_retry_preserves_failed_receipt_and_trace(self):
        request = {'model': 'test-model', 'role': 'predictor', 'prompt': 'Offline synthetic test',
                   'payload': {}, 'response_schema': {}}
        failed = SimpleNamespace(returncode=1,
                                 stdout=json.dumps({'type': 'error', 'message': 'synthetic capacity failure'}),
                                 stderr='synthetic transport diagnostic')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = CodexAgentBackend(folder, 'unused-test-cli', 'test-model')
            with patch('pilot.social_tradeoffs.agent_pair.subprocess.run', return_value=failed):
                with self.assertRaises(RuntimeError):
                    backend.generate(request)
                original = next(folder.rglob('handoff.json'))
                original_bytes = original.read_bytes()
                with self.assertRaises(RuntimeError):
                    backend.generate(request)
            self.assertEqual(original.read_bytes(), original_bytes)
            self.assertEqual(len(list(folder.rglob('handoff.json'))), 2)
            self.assertEqual(len(list(folder.rglob('trace.jsonl'))), 2)
