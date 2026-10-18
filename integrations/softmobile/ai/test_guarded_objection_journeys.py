"""Fictional 20-turn regression for the private suggestion guard, offline only."""
import unittest

from groq_sales_objections import JOURNEYS
from journey_memory import history_snapshot
from sales_quality_gate import assess
from suggestion_guard import guarded_draft

class GuardedObjectionJourneys(unittest.TestCase):
    def test_generic_drafts_replaced_with_topic_specific_review(self):
        checked=0
        for journey in JOURNEYS:
            prior=[]
            for buyer,topic,_requires_human in journey["turns"]:
                with self.subTest(journey=journey["id"],turn=checked,topic=topic):
                    clean={"message":buyer,"context":history_snapshot(prior[-4:])}
                    answer,blocked=guarded_draft(
                        {"suggested_reply":"Gracias por consultar.","human_review":False},clean)
                    marks=assess(answer["suggested_reply"],topic)
                    self.assertTrue(blocked)
                    self.assertTrue(answer["human_review"])
                    self.assertTrue(all(marks[k] for k in
                        ("relevant","actionable","specific","meaningful")),marks)
                prior.append(buyer)
                checked+=1
        self.assertEqual(checked,20)

    def test_price_or_reservation_promises_never_survive(self):
        checked=0
        for journey in JOURNEYS:
            for buyer,topic,_ in journey["turns"]:
                with self.subTest(journey=journey["id"],turn=checked):
                    answer,blocked=guarded_draft(
                        {"suggested_reply":"Te lo reservo, cuesta L 13,000","human_review":False},
                        {"message":buyer})
                    self.assertTrue(blocked)
                    self.assertTrue(answer["human_review"])
                    self.assertNotIn("13,000",answer["suggested_reply"])
                checked+=1
        self.assertEqual(checked,20)

if __name__=="__main__":
    unittest.main()
