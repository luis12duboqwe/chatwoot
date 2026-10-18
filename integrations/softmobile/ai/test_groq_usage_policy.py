"""Development-only API usage switch; execution/deployment limits remain separate."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import groq_usage_policy as policy

class UsagePolicyTests(unittest.TestCase):
    def test_missing_flag_preserves_default_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(policy, 'FLAG', Path(temp) / 'missing'):
                self.assertFalse(policy.unlimited_development())
                self.assertEqual(policy.request_cap(160), 160)
                self.assertEqual(policy.request_cap(30), 30)

    def test_enabled_secure_flag_has_no_daily_api_cap(self):
        if os.getuid() != 0:
            self.skipTest('Root-owned operator flag')
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'enable'
            marker.write_text('development')
            marker.chmod(0o600)
            with patch.object(policy, 'FLAG', marker):
                self.assertTrue(policy.unlimited_development())
                self.assertEqual(policy.request_cap(160), sys.maxsize)
                self.assertEqual(policy.request_cap(4), sys.maxsize)

    def test_world_writable_switch_not_trusted(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'unsafe'
            marker.write_text('development')
            marker.chmod(0o666)
            with patch.object(policy, 'FLAG', marker):
                self.assertFalse(policy.unlimited_development())
                self.assertEqual(policy.request_cap(160), 160)

    def test_invalid_defaults_rejected(self):
        for value in (0, -1, False, '160'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy.request_cap(value)
