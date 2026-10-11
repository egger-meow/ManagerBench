import sys
import unittest
from unittest.mock import patch

from pilot.social_tradeoffs.llm import handle_interactive_error


class TestInteractiveErrorHandler(unittest.TestCase):
    def test_non_interactive_returns_none(self):
        with patch('sys.stdin.isatty', return_value=False):
            choice = handle_interactive_error('call-01', code=429, error_kind='rate_limited')
            self.assertIsNone(choice)

    def test_interactive_choice_wait_retry(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', side_effect=['1', '5']):
            action, delay = handle_interactive_error('call-01', code=503, error_kind='ambiguous')
            self.assertEqual(action, 'retry_wait')
            self.assertEqual(delay, 5)

    def test_interactive_choice_update_key(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', side_effect=['2', 'AIzaSyNewKey123']):
            action, new_key = handle_interactive_error('call-01', code=429, error_kind='rate_limited')
            self.assertEqual(action, 'update_key')
            self.assertEqual(new_key, 'AIzaSyNewKey123')

    def test_interactive_choice_switch_agent(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', return_value='3'):
            action, val = handle_interactive_error('call-01', code=429, error_kind='rate_limited')
            self.assertEqual(action, 'switch_agent')
            self.assertIsNone(val)

    def test_interactive_choice_exit(self):
        with patch('sys.stdin.isatty', return_value=True), \
             patch('builtins.input', return_value='4'):
            action, val = handle_interactive_error('call-01', error_kind='max_attempts')
            self.assertEqual(action, 'exit')
            self.assertIsNone(val)


if __name__ == '__main__':
    unittest.main()
