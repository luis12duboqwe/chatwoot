#!/usr/bin/env python3
"""Offline transport observer regression tests; never send WhatsApp messages."""
from datetime import datetime,timezone,timedelta
import io,json
from unittest import TestCase,main
from unittest.mock import patch
import pilot_transport_monitor as monitor

class TransportTests(TestCase):
 def setUp(self):
  self.t=datetime(2026,10,17,22,0,tzinfo=timezone.utc)
  self.payload={"account_id":2,"inbox_id":2,
    "incoming_total":42,"public_total":40,"bot_total":33,
    "public_status_counts":{"sent":40},
    "latest_incoming_id":211,
    "latest_incoming_kind":"question_or_purchase",
    "latest_incoming_at":(self.t-timedelta(minutes=2)).isoformat(),
    "latest_bot_for_incoming":True,
    "manual_reply_after_last_incoming":False}
  self.good={"session_count":1,"working":1,"all_working":True}
 def test_marked_sent_is_not_delivery_claim(self):
  self.assertEqual(monitor.classify(self.payload,self.good,at=self.t),"chatwoot_bot_reply_recorded")
  with patch.object(monitor,"rails_snapshot",return_value=self.payload),patch.object(monitor,"waha_status",return_value=self.good):
   with patch.object(monitor,"_atomic_json") as write:
    x=monitor.run()
    self.assertFalse(x["physical_phone_delivery_verified"])
    self.assertNotIn("delivered",x["status"])
    self.assertNotIn("secret",json.dumps(x))
    write.assert_called_once()
 def test_no_whatsapp_network_connection_in_code(self):
  # WAHA only GET session statuses; no send endpoints or mutations.
  self.assertEqual(monitor.WAHA_URL,"http://127.0.0.1:3201/api/sessions")
  self.assertNotIn("sendText",monitor.WAHA_URL)
 def test_missing_recent_reply_not_false_alarm(self):
  sample=dict(self.payload,latest_bot_for_incoming=False)
  self.assertEqual(monitor.classify(sample,self.good,at=self.t),"pending_recent_inbound")
 def test_stale_inbound_requires_review(self):
  sample=dict(self.payload,latest_bot_for_incoming=False,
    latest_incoming_at=(self.t-timedelta(minutes=20)).isoformat())
  self.assertEqual(monitor.classify(sample,self.good,at=self.t),"unanswered_inbound_needs_review")
 def test_ack_after_customer_answer_is_not_missing_reply(self):
  sample=dict(self.payload,latest_incoming_kind="ack",latest_bot_for_incoming=False,
      latest_incoming_at=(self.t-timedelta(minutes=60)).isoformat())
  self.assertEqual(monitor.classify(sample,self.good,at=self.t),"ack_no_public_reply_expected")

 def test_manual_reply_is_not_bot_failure(self):
  sample=dict(self.payload,latest_bot_for_incoming=False,manual_reply_after_last_incoming=True,
    latest_incoming_at=(self.t-timedelta(hours=1)).isoformat())
  self.assertEqual(monitor.classify(sample,self.good,at=self.t),"human_reply_recorded")
 def test_waha_down_is_precedence(self):
  self.assertEqual(monitor.classify(self.payload,{"all_working":False},at=self.t),"transport_unhealthy")
 def test_rails_scope_and_read_only(self):
  class Fake:
   returncode=0
   stdout=monitor.MARK+json.dumps(self.payload)+"\n"
  def runner(cmd,**kwargs):
   text=kwargs["input"]
   self.assertIn("Conversation.find_by(id:3)",text)
   self.assertIn("c.account_id==2 && c.inbox_id==2",text)
   self.assertNotIn("Messages::MessageBuilder",text)
   self.assertNotIn(".perform",text)
   return Fake()
  self.assertEqual(monitor.rails_snapshot(runner=runner)["bot_total"],33)
 def test_wrong_inbox_rejected(self):
  class Fake:
   returncode=0
   stdout=monitor.MARK+json.dumps(dict(self.payload,inbox_id=5))+"\n"
  with self.assertRaises(RuntimeError):monitor.rails_snapshot(runner=lambda *a,**k:Fake())
 def test_waha_credential_not_in_result(self):
  class FakeCmd:
   returncode=0
   stdout=json.dumps([{"Config":{"Env":["WAHA_API_KEY_PLAIN=secret-test","SOMETHING=other"]}}])
  class FakeResponse(io.BytesIO):
   status=200
   def __enter__(self):return self
   def __exit__(self,*exc):return False
  def opener(req,**kwargs):
   self.assertEqual(req.get_header("X-api-key"),"secret-test")
   self.assertEqual(req.get_method(),"GET")
   return FakeResponse(json.dumps([{"status":"WORKING","name":"private-session-name","me":{"id":"5551111111"}}]).encode())
  result=monitor.waha_status(runner=lambda *a,**k:FakeCmd(),opener=opener)
  self.assertEqual(result,{"session_count":1,"working":1,"all_working":True})
  self.assertNotIn("secret-test",str(result))
  self.assertNotIn("private-session-name",str(result))

if __name__=="__main__":main()
