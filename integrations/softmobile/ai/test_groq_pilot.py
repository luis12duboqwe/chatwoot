#!/usr/bin/env python3
"""Offline, no network, no customer messages."""
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch
import groq_pilot as pilot

class TestGroqPilot(unittest.TestCase):
    def setUp(self):
        self.case = {"conversation_id": 3, "message": "¿Tienen Samsung S22 Ultra de 256 negro?",
                     "context": {"city": "Choloma"}}
        self.answer = {"intent": "consulta", "model": "Samsung S22 Ultra",
                       "storage_gb": 256, "color_options": ["negro"], "city": "Choloma",
                       "pickup_location": None, "human_review": False,
                       "suggested_reply": "¿Lo querés retirar en Choloma o preferís envío?"}

    def test_pilot_only(self):
        for value in (2, 4, "3", None, True):
            with self.subTest(value=value), self.assertRaises(pilot.PilotError):
                pilot.prepare(dict(self.case, conversation_id=value))

    def test_pilot_works(self):
        clean = pilot.prepare(self.case)
        self.assertEqual(clean["conversation_id"], 3)
        self.assertIn("Samsung", clean["message"])

    def test_input_size_and_type(self):
        for data in ({"conversation_id": 3, "message": "x" * 1501},
                     {"conversation_id": 3, "message": ""}, [],
                     {"conversation_id": 3, "message": "ok", "context": []}):
            with self.subTest(data=str(data)[:30]), self.assertRaises(pilot.PilotError):
                pilot.prepare(data)

    def test_context_is_whitelisted(self):
        x = pilot.prepare({"conversation_id": 3, "message": "hola", "context": {
            "city": "Choloma", "api_key": "SECRET-NOT-ALLOWED",
            "credit_card": "4111111111111111"}})
        self.assertEqual(x["context"], {"city": "Choloma"})
        self.assertNotIn("SECRET", repr(x))

    def test_redaction(self):
        s = pilot.redact("Correo prueba@ejemplo.com; cel +504 9999-1234; "
                         "tarjeta 4111111111111111; https://example.com/x")
        self.assertNotIn("prueba@", s)
        self.assertNotIn("4111111111111111", s)
        self.assertNotIn("9999-1234", s)
        self.assertNotIn("https://", s)

    def test_structured_schema(self):
        out = pilot.payload(pilot.prepare(self.case))
        self.assertEqual(out["response_format"]["json_schema"]["strict"], True)
        self.assertEqual(set(out["response_format"]["json_schema"]["schema"]["required"]),
                         set(out["response_format"]["json_schema"]["schema"]["properties"]))
        self.assertEqual(out["model"], "openai/gpt-oss-20b")

    def test_no_key_no_live_call(self):
        clean = pilot.prepare(self.case)
        with patch.dict(os.environ, {"SOFTMOBILE_AI_ENABLED": "false"}), self.assertRaises(pilot.PilotError):
            pilot.suggest(clean, "any")
        with patch.dict(os.environ, {"SOFTMOBILE_AI_ENABLED": "true"}), self.assertRaises(pilot.PilotError):
            pilot.suggest(clean, "")

    def test_mocked_groq_request(self):
        clean = pilot.prepare(self.case)
        expected = self.answer.copy()
        expected["human_review"] = True
        result = {"choices": [{"message": {"content": json.dumps(self.answer)}}]}
        class Reply(io.BytesIO):
            status = 200
        def opener(req, timeout):
            self.assertEqual(req.full_url, pilot.ENDPOINT)
            self.assertEqual(timeout, 12)
            self.assertEqual(req.get_header("Authorization"), "Bearer mock-test-key")
            body = json.loads(req.data)
            self.assertEqual(body["messages"][0]["role"], "system")
            return Reply(json.dumps(result).encode())
        with patch.dict(os.environ, {"SOFTMOBILE_AI_ENABLED": "true"}):
            self.assertEqual(pilot.suggest(clean, "mock-test-key", opener), expected)

    def test_reject_malformed_model_output(self):
        clean = pilot.prepare(self.case)
        for invalid in ({"intent": "consulta"}, dict(self.answer, storage_gb="256"),
                        dict(self.answer, suggested_reply="x" * 351),
                        dict(self.answer, color_options=["negro"] * 20),
                        dict(self.answer, human_review="false")):
            with self.subTest(invalid=list(invalid.keys())), self.assertRaises(pilot.PilotError):
                pilot.validate(invalid, clean)

    def test_sensitive_topics_force_human(self):
        for message in ("¿Cuál es el precio?", "¿Tienen fotos?", "¿Hacen reservas?",
                        "¿Me dan garantía?", "¿Aceptan pago por transferencia?"):
            out = pilot.validate(dict(self.answer), pilot.prepare(
                {"conversation_id": 3, "message": message}))
            self.assertTrue(out["human_review"], message)

    def test_cli_dry_run_requires_no_api_key(self):
        result = subprocess.run([sys.executable, pilot.__file__],
                                input=json.dumps(self.case), text=True,
                                capture_output=True, check=True, env={"PATH": os.getenv("PATH", "")})
        out = json.loads(result.stdout)
        self.assertEqual(out["status"], "dry_run")
        self.assertFalse(out["external_call"])
        self.assertFalse(out["sent_to_customer"])
        self.assertNotIn("Samsung", result.stdout)

if __name__ == "__main__":
    unittest.main()
