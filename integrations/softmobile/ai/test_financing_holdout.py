import unittest
import financing_holdout as f

class HoldoutTests(unittest.TestCase):
 def test_unseen_phrases_cover_ten_eighteen_twentyfour_thirtysix(self):
  data=f.scenarios()
  self.assertEqual(len(data),48)
  self.assertEqual(len({x['id'] for x in data}),48)
  self.assertEqual(len(f.TEMPLATES),4)
  self.assertTrue(all(len(x['messages'])==2 for x in data))
  self.assertTrue(any('24 cuotas' in x['messages'][1] for x in data))
 def test_no_money_amounts_or_client_identifiers_in_fixtures(self):
  for x in f.scenarios():
   self.assertEqual(x['expected'],'not_found')
   self.assertTrue(x['messages'][0].startswith('Me interesa'))
   self.assertNotIn('@',str(x['messages']))
   self.assertNotIn('http',str(x['messages']))
if __name__=='__main__':unittest.main()
