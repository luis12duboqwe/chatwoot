#!/usr/bin/env python3
"""Offline tests for the interactive Groq key installer. No actual secrets or network."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import configurar_clave_groq as config

SAMPLE_KEY = "gsk_" + "a" * 32

class TestInstaller(unittest.TestCase):
    def test_private_permissions_and_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "secrets" / "groq.env"
            config.save_key(SAMPLE_KEY, dest)
            self.assertEqual(config.stored_key(dest), SAMPLE_KEY)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            self.assertEqual(sorted(p.name for p in dest.parent.iterdir()), ["groq.env"])

    def test_replace_atomic(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "groq.env"
            config.save_key(SAMPLE_KEY, dest)
            second = "gsk_" + "b" * 32
            config.save_key(second, dest)
            self.assertEqual(config.stored_key(dest), second)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)

    def test_rejects_invalid_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "groq.env"
            for secret in ("", "ghp_" + "x" * 20, "gsk_injection\nGROQ_API_KEY=oops", "gsk_short"):
                with self.subTest(secret=secret[:9]), self.assertRaises(ValueError):
                    config.save_key(secret, dest)
            self.assertFalse(dest.exists())

    def test_rejects_bad_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "groq.env"
            config.save_key(SAMPLE_KEY, dest)
            dest.chmod(0o644)
            with self.assertRaises(RuntimeError):
                config.stored_key(dest)

    def test_simulated_provider_verify(self):
        class Fake:
            returncode = 0
            stdout = json.dumps({"status": "suggestion_only", "sent_to_customer": False,
                                 "proposal": {"suggested_reply": "¿Qué modelo buscás?"}})
        def mocked_run(args, **kwargs):
            self.assertEqual(kwargs["env"]["GROQ_API_KEY"], SAMPLE_KEY)
            self.assertEqual(kwargs["env"]["SOFTMOBILE_AI_ENABLED"], "true")
            self.assertEqual(json.loads(kwargs["input"])["conversation_id"], 3)
            self.assertIn("--live", args)
            return Fake()
        with patch.object(config.subprocess, "run", side_effect=mocked_run):
            self.assertEqual(config.verify(SAMPLE_KEY)["suggested_reply"], "¿Qué modelo buscás?")

if __name__ == "__main__":
    unittest.main()
