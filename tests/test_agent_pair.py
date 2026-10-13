"""Offline coordinator checks; no real agent or participant data is used."""
import json
from pathlib import Path
import unittest

from pilot.social_tradeoffs.agent_pair import codex_command, validate_trace


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
