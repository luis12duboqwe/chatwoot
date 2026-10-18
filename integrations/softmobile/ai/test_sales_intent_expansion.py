#!/usr/bin/env python3
"""Offline coverage for context-sensitive, PRIVATE commercial suggestion guard."""
import unittest
from suggestion_guard import _buyer_topic, _topic_fallback, guarded_draft
from sales_quality_gate import assess

class SalesIntentExpansionTests(unittest.TestCase):
    CASES=[
        ("No quiero negro, mejor 256GB blanco","product"),
        ("¿Y el negro de 128GB cuesta lo mismo?","comparison"),
        ("Quiero llevármelo hoy, ¿me lo apartan?","closing"),
        ("Prefiero el azul, por favor","product"),
        ("¿Cuál cuesta más?","comparison"),
        ("¿Me lo reservan?","closing"),
    ]
    def test_commercial_followups_identified(self):
        for question, topic in self.CASES:
            with self.subTest(question=question):
                self.assertEqual(_buyer_topic({"message":question}),topic)
    def test_every_fallback_has_specific_action_without_commitment(self):
        for question,topic in self.CASES:
            with self.subTest(question=question):
                clean={"message":question}
                draft=_topic_fallback(clean)
                score=assess(draft,topic)
                self.assertTrue(all(score[k] for k in ("relevant","actionable","specific","meaningful")),score)
                self.assertNotIn("está disponible",draft.lower())
                self.assertNotIn("apartado",draft.lower())
    def test_vague_groq_drafts_are_repaired_with_review(self):
        for question,topic in self.CASES:
            with self.subTest(question=question):
                candidate={"suggested_reply":"Gracias por escribir.","human_review":False}
                cleaned,blocked=guarded_draft(candidate,{"message":question})
                self.assertTrue(blocked)
                self.assertTrue(cleaned["human_review"])
                self.assertTrue(assess(cleaned["suggested_reply"],topic)["relevant"])
    def test_valid_relevant_draft_is_preserved(self):
        clean={"message":"¿Y el negro de 128GB cuesta lo mismo?"}
        valid={"suggested_reply":_topic_fallback(clean),"human_review":True}
        draft,blocked=guarded_draft(valid,clean)
        self.assertFalse(blocked)
        self.assertEqual(draft,valid)
    def test_no_guaranteed_pricing_or_reservation(self):
        for question,_ in self.CASES:
            proposed={"suggested_reply":"Te lo reservo, cuesta L. 13,000","human_review":False}
            result,blocked=guarded_draft(proposed,{"message":question})
            self.assertTrue(blocked)
            self.assertTrue(result["human_review"])
            self.assertNotIn("13,000",result["suggested_reply"])
if __name__=="__main__": unittest.main()
