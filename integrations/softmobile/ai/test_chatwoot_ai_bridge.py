#!/usr/bin/env python3
"""No Chatwoot writes, no external network; deterministic checks for pilot bridge."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import chatwoot_ai_bridge as bridge

class BridgeTests(unittest.TestCase):
    def test_safe_text_rejects_personal_or_multimedia(self):
        allowed = ["Tengo interés en un iPhone 14 Pro Max", "S22 Ultra morado 256 GB, ¿lo venden?"]
        for m in allowed:
            self.assertEqual(bridge.safe_text(m), m)
        blocked = ["", "ok", "x" * 601, "Mi celular 9999-1234",
                   "mi correo hola@example.com", "http://example.org",
                   "mi contraseña es 123", "Mi identidad es secreta",
                   "tarjeta 4111111111111111","Gasolinera uno",
                   "Frente al parque en Comayagua", "Colonia las Palmas"]
        for m in blocked:
            with self.subTest(m=m[:30]):
                self.assertIsNone(bridge.safe_text(m))
        for m in ("Hola", "Ok", "Efectivo", "Galerías"):
            self.assertIsNone(bridge.safe_text(m))

    def test_latest_cursor_parses_expected_rails(self):
        def fake_rails(code):
            self.assertIn("Conversation.find_by(id:3)", code)
            self.assertIn("c.account_id==2 && c.inbox_id==2", code)
            self.assertIn("maximum(:id)", code)
            return {"id":13}
        with patch.object(bridge, "rails_run", side_effect=fake_rails):
            self.assertEqual(bridge.latest_id(),13)

    def test_get_next_strict_filter(self):
        def fake_rails(code):
            self.assertIn("id > ?",code)
            self.assertIn("private: false",code)
            self.assertIn("reorder(id: :desc)",code)
            self.assertIn("limit(4)", code)
            self.assertIn("history:prior",code)
            self.assertIn("age_seconds:", code)
            return {"id":20,"content":"Samsung","has_attachments":False}
        with patch.object(bridge, "rails_run", side_effect=fake_rails):
            self.assertEqual(bridge.get_next(13)["id"],20)
            with self.assertRaises(ValueError):
                bridge.get_next(-1)

    def test_private_notes_are_enforced_in_rails(self):
        sample=bridge.format_note("14",{
            "suggested_reply":"Podemos verificar las opciones con un vendedor.",
            "human_review":True})
        def fake_rails(code):
            self.assertIn("private:true",code)
            self.assertIn("private:true",code)
            self.assertIn("MessageBuilder.new(nil,c,",code)
            self.assertIn("unless confirmed && confirmed.private?",code)
            self.assertNotIn("private:false}).perform",code)
            self.assertIn("invalid inbound",code)
            self.assertIn("superseded inbound",code)
            self.assertIn("inbound.maximum(:id)==token.to_i",code)
            return {"status":"created","private":True}
        with patch.object(bridge,"rails_run", side_effect=fake_rails):
            self.assertEqual(bridge.put_private("14",sample),"created")
            self.assertEqual(bridge.put_private("DEMO-1",
                bridge.format_note("DEMO-1",{"suggested_reply":"Consulta de prueba.",
                                           "human_review":False})),"created")

    def test_invalid_marker_and_note_fail_closed(self):
        with self.assertRaises(ValueError):
            bridge.put_private("14;DROP", "x"*40)
        with self.assertRaises(ValueError):
            bridge.put_private("14", "short")

    def test_state_atomic_private_and_valid(self):
        with tempfile.TemporaryDirectory() as dir:
            filename=Path(dir)/"state.json"
            with patch.object(bridge,"STATE",filename):
                state={"pilot":3,"after_id":13,"day":"","calls":0}
                bridge.save_state(state)
                self.assertEqual(bridge.load_state(),state)
                self.assertEqual(filename.stat().st_mode & 0o777,0o600)
                filename.chmod(0o644)
                with self.assertRaises(RuntimeError):
                    bridge.load_state()

    def test_disabled_does_not_query_or_write(self):
        with patch.dict(bridge.os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):
                bridge.run_once()

    def test_normal_run_one_message_once(self):
        with tempfile.TemporaryDirectory() as dir:
            filename=Path(dir)/"state.json"
            with patch.object(bridge,"STATE",filename):
                bridge.save_state({"pilot":3,"after_id":13,"day":"","calls":0})
                mock_reply={"suggested_reply":"Un vendedor puede confirmar.", "human_review":True}
                with patch.dict(bridge.os.environ,{"SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED":"true"}):
                    with patch.object(bridge,"get_next",side_effect=[
                        {"id":14,"content":"Quiero el Samsung S22 Ultra 256 GB","age_seconds":5,"has_attachments":False,
                         "history":["Busco un Samsung S22 Ultra negro 128 GB","Mejor el azul para Choloma"]},
                        {"id":None}
                    ]), patch.object(bridge,"suggest",return_value=mock_reply) as sg, \
                         patch.object(bridge,"stored_key",return_value="mock") as sk, \
                         patch.object(bridge,"put_private",return_value="created") as pn:
                        self.assertEqual(bridge.run_once(),"private_note_created")
                        self.assertEqual(bridge.load_state()["after_id"],14)
                        self.assertEqual(bridge.run_once(),"no_new_messages")
                        self.assertEqual(sg.call_count,1)
                        context_sent=sg.call_args.args[0]["context"]
                        self.assertEqual(context_sent["model"],"Samsung S22 Ultra")
                        self.assertEqual(context_sent["storage_gb"],"128")
                        self.assertEqual(context_sent["color_options"],"azul")
                        self.assertEqual(context_sent["city"],"Choloma")
                        self.assertEqual(pn.call_count,1)
                        private_note=pn.call_args.args[1]
                        self.assertIn("Ficha comercial:",private_note)
                        self.assertIn("Samsung S22 Ultra",private_note)
                        self.assertIn("Color: azul",private_note)
                        self.assertIn("Ciudad: Choloma",private_note)
                        self.assertIn("NO ENVIADA AL CLIENTE",private_note)
                        self.assertLess(len(private_note),1500)
                        self.assertEqual(sk.call_count,1)

    def test_sensitive_message_skips_without_calling_groq(self):
        with tempfile.TemporaryDirectory() as dir:
            with patch.object(bridge,"STATE",Path(dir)/"state.json"):
                bridge.save_state({"pilot":3,"after_id":13,"day":"","calls":0})
                with patch.dict(bridge.os.environ,{"SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED":"true"}):
                    with patch.object(bridge,"get_next",return_value={
                        "id":14,"content":"Escribime al 9999-1234",
                        "age_seconds":5,"has_attachments":False
                    }), patch.object(bridge,"suggest") as fake_groq:
                        self.assertEqual(bridge.run_once(),"skipped_sensitive_or_multimedia")
                        self.assertEqual(bridge.load_state()["after_id"],14)
                        fake_groq.assert_not_called()

    def test_stale_message_is_skipped_without_api(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(bridge, "STATE", Path(directory)/"state.json"):
                bridge.save_state({"pilot":3,"after_id":13,"day":"","calls":0})
                with patch.dict(bridge.os.environ, {"SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED":"true"}):
                    with patch.object(bridge, "get_next", return_value={
                        "id":212,"content":"¿Busco el iPhone 14 Pro Max?",
                        "age_seconds":480,"has_attachments":False}), \
                         patch.object(bridge, "suggest") as api, \
                         patch.object(bridge, "put_private") as note:
                        self.assertEqual(bridge.run_once(), "skipped_stale")
                        self.assertEqual(bridge.load_state()["after_id"], 212)
                        self.assertEqual(bridge.load_state()["calls"], 0)
                        api.assert_not_called()
                        note.assert_not_called()

    def test_short_acknowledgment_is_not_sent_to_api(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(bridge, "STATE", Path(directory)/"state.json"):
                bridge.save_state({"pilot":3,"after_id":190,"day":"","calls":0})
                with patch.dict(bridge.os.environ, {"SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED":"true"}):
                    with patch.object(bridge, "get_next", return_value={
                        "id":212,"content":"Ok","age_seconds":8,
                        "has_attachments":False}), \
                         patch.object(bridge, "suggest") as api:
                        self.assertEqual(bridge.run_once(), "skipped_sensitive_or_multimedia")
                        self.assertEqual(bridge.load_state()["after_id"], 212)
                        api.assert_not_called()

    def test_transient_failure_has_daily_budget(self):
        with tempfile.TemporaryDirectory() as dir:
            with patch.object(bridge,"STATE",Path(dir)/"state.json"):
                bridge.save_state({"pilot":3,"after_id":13,"day":"","calls":0})
                with patch.dict(bridge.os.environ,{"SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED":"true"}):
                    with patch.object(bridge,"get_next",return_value={
                            "id":14,"content":"¿Tienen iPhone 14 Pro Max?",
                            "age_seconds":5,"has_attachments":False
                        }), patch.object(bridge,"stored_key",return_value="test"), \
                         patch.object(bridge,"suggest",side_effect=bridge.PilotError("timeout")):
                        self.assertEqual(bridge.run_once(),"safe_fallback")
                        self.assertEqual(bridge.load_state()["after_id"],13)
                        self.assertEqual(bridge.load_state()["calls"],1)
                        state=bridge.load_state()
                        state["calls"]=bridge.MAX_DAILY_REQUESTS
                        bridge.save_state(state)
                        self.assertEqual(bridge.run_once(),"daily_limit")

if __name__=="__main__":
    unittest.main()
