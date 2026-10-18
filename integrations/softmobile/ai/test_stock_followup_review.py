import unittest
from unittest.mock import patch
import stock_followup_review as q

class StockFollowupReviewTests(unittest.TestCase):
 def test_source_exact_sha_blocks_old_or_unrelated_ruby(self):
  with self.assertRaises(ValueError):q.build("unreviewed code")
 def test_reply_text_has_a_next_question_and_does_not_sell_fake_inventory(self):
  self.assertIn("¿De cuántos GB y en qué color lo buscás?",q.AFTER)
  self.assertIn("no tengo existencias confirmadas",q.AFTER)
  for unsafe in ["Sí, tenemos disponible", "Precio L", "ya reservado"]:
   self.assertNotIn(unsafe,q.AFTER)
 def test_fictional_buyer_question_can_be_scored_without_public_messaging(self):
  text="¿De cuántos GB y en qué color lo buscás?"
  def fake(cases,source=None):
   return [{"id":x["id"],"turns":[{"bot":text}]}
           for x in cases]
  with patch.object(q.replay,"isolated_replay",side_effect=fake):
   x=q.smoke("synthetic ruby source")
  self.assertEqual(x["total"],5)
  self.assertEqual(x["passed"],3)
  self.assertEqual(x["public_messages_sent"],0)
 def test_unsafe_confirmation_cannot_pass(self):
  def fake(cases,source=None):
   return [{"id":x["id"],"turns":[{"bot":"Sí tenemos en stock. El precio es L9000. ¿De cuántos GB y en qué color lo buscás?"}]}
           for x in cases]
  with patch.object(q.replay,"isolated_replay",side_effect=fake):
   result=q.smoke("synthetic ruby")
  self.assertEqual(result["passed"],0)
if __name__=="__main__":unittest.main()
