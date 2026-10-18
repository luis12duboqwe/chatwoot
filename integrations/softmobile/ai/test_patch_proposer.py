#!/usr/bin/env python3
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import patch_proposer as p
import synthetic_lab as s

class PatchProposerTests(unittest.TestCase):
 def setUp(self):
  self.src=("PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n"+
    p.START+"      old = :value\n      data[:color] = old\n"+("      # context fixture\n"*20)+"      data\n    end\n\n"+
    p.STOP+"\n")
  self.proposal={"search":"      old = :value\n","replace":"      old = :changed\n",
    "reason":"El color debe respetar los cambios de preferencia.",
    "regression_example":"El comprador cambia de azul a rojo; devolver rojo."}
  self.issue={"id":"6080c2a5b31ef5b2a9","status":"synthetic_unverified",
     "source":"interactive_step_by_step_groq","at":"2026-10-17T23:24:00Z",
     "scenario":{"category":"changes","messages":[
        "Busco iPhone 15 Pro en negro de 128 GB",
        "Ahora quiero 256GB en azul",
        "Mejor 128GB en rojo"]},
     "evidence":[{"buyer":"Busco iPhone 15 Pro en negro de 128 GB","bot":"Revisaré 128GB negro"},
                 {"buyer":"Ahora quiero 256GB en azul","bot":"Revisaré 256GB negro"},
                 {"buyer":"Mejor 128GB en rojo","bot":"Revisaré 128GB azul"}]}
 def test_source_and_target_isolation(self):
  with patch.object(p,"START","    def context_from(texts)\n"),patch.object(p,"STOP","    # Photo requests with two distinct models"):
   with self.assertRaises(ValueError):p.method_area("module Fake; end")
 def test_proposal_rejects_arbitrary_code_and_methods(self):
  for replacement in (
   "      eval('anything')\n",
   "      File.write('/tmp/out','unsafe')\n",
   "      system('unsafe')\n",
   "      ENV['KEY']\n",
   "      thing = \x60echo hacked\x60\n",
   "      data = Net::HTTP.start('example')\n",
   "      old = :value\n    def steal();end\n",
  ):
   with self.subTest(replacement=replacement),self.assertRaises(ValueError):
    p.validate_patch(self.src,dict(self.proposal,replace=replacement))
 def test_reject_no_effect_color_reset(self):
  source=("PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n"+
     p.START+"      choices=color_options(variant_str)\n      if choices.any?\n"+
     "        data[:color_options]=choices\n        data[:color]=choices.first\n"+
     "      end\n"+("      # unchanged source\n"*20)+"      data\n    end\n\n"+
     p.STOP+"\n")
  proposal={"search":"      if choices.any?\n        data[:color_options]=choices\n        data[:color]=choices.first\n",
   "replace":"      if choices.any?\n        data[:color]=nil\n"+
     "        data[:color_options]=choices\n        data[:color]=choices.first\n",
   "reason":"Intento de borrar color", "regression_example":"cambio color"}
  with self.assertRaisesRegex(ValueError,"overwritten"):
   p.validate_patch(source,proposal)
 def test_exact_unique_match_required(self):
  src=self.src.replace("      old = :value\n","      old = :value\n      old = :value\n")
  with self.assertRaises(ValueError):p.validate_patch(src,self.proposal)
  with self.assertRaises(ValueError):p.validate_patch(self.src,dict(self.proposal,search="      not present\n"))
 def test_small_scoped_proposal_passes_static_checks(self):
  candidate=p.validate_patch(self.src,self.proposal)
  self.assertIn(":changed",candidate)
  self.assertIn(p.STOP,candidate)
  self.assertEqual(candidate.count("PILOT_CONVERSATION_ID = 3"),1)
 def test_ruby_syntax_is_parse_only_and_no_exec(self):
  class Outcome:returncode=0;stdout="Syntax OK\n"
  def fake_runner(argv,**args):
   self.assertEqual(argv[0:2],["docker","run"])
   self.assertIn("--network",argv)
   self.assertIn("none",argv)
   self.assertIn("--read-only",argv)
   self.assertIn("--cap-drop",argv)
   self.assertIn("--user",argv)
   self.assertIn("65534:65534",argv)
   self.assertNotIn("softmobile-chatwoot-rails-1",argv)
   self.assertEqual(argv[-2:],["-c","-"])
   self.assertEqual(args["input"],self.src)
   return Outcome()
  self.assertTrue(p.syntax_only(self.src,runner=fake_runner))
 def test_proposals_are_inert_and_private(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(p,"STAGE",Path(tmp)):
   candidate=p.validate_patch(self.src,self.proposal)
   output=p.stage(self.src,candidate,self.proposal,self.issue)
   self.assertFalse(output["model_code_executed"])
   self.assertFalse(output["automatic_deployment_allowed"])
   self.assertEqual((Path(tmp)/(output["proposal_id"]+".diff")).stat().st_mode&0o777,0o600)
   diff=(Path(tmp)/(output["proposal_id"]+".diff")).read_text()
   self.assertIn("+      old = :changed",diff)
 def test_select_realistic_interactive_change_issue(self):
  self.assertEqual(p.pick_issue([self.issue])["id"],self.issue["id"])
  self.assertIsNone(p.pick_issue([dict(self.issue,status="closed")]))
  bad=dict(self.issue,scenario={"category":"changes","messages":[
      "Mi tarjeta 4111111111111111","256GB en rojo","Gracias"]})
  self.assertIsNone(p.pick_issue([bad]))
 def test_generator_never_exposes_private_channels(self):
  src=Path(p.__file__).read_text()
  self.assertNotIn("MessageBuilder",src)
  self.assertNotIn("sendText",src)
  self.assertNotIn("fixer.deploy(",src)
  self.assertNotIn("rails runner -",src)
  self.assertNotIn("subprocess.Popen",src)
 def test_sanity_guards_on_response_structure(self):
  with self.assertRaises(ValueError):p.validate_patch(self.src,{**self.proposal,"unexpected":"true"})
  with self.assertRaises(ValueError):p.validate_patch(self.src,dict(self.proposal,replace=self.proposal["search"]))
  with self.assertRaises(ValueError):p.validate_patch(self.src,dict(self.proposal,replace="x"*2000))

if __name__=="__main__":unittest.main()
