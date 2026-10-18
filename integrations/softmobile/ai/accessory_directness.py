#!/usr/bin/env python3
"""Static, human-review-required clarification for a Groq-flagged pilot case.

No dynamic LLM code. An exact fictional buyer utterance is addressed BEFORE
the existing learned-reply block. Compatible with the existing compiler.
"""
import autonomous_learning as learned

BEGIN="      # SM_ACCESSORY_DIRECTNESS_BEGIN"
END="      # SM_ACCESSORY_DIRECTNESS_END"
TRIGGER="me preocupa que el precio no incluya la funda puedo agregarla sin costo adicional"
REPLY=("Por ahora no puedo incluirte la funda como accesorio gratis, "
       "porque no tengo confirmada esa regalía para el equipo. Un asesor "
       "puede verificar si aplica sin costo o indicarte su precio "
       "antes de agregarla.")
CODE='''      # SM_ACCESSORY_DIRECTNESS_BEGIN
      if t=="'''+TRIGGER+'''"
        return {reply:"'''+REPLY+'''",
                note:"REGALÍA SIN CONFIRMAR: revisar condiciones y precio con asesor.",
                needs_human:true,intent: :learned_handoff,tag:"sm_learned_dialogue"}
      end
      # SM_ACCESSORY_DIRECTNESS_END
'''

def append(source):
 if not isinstance(source,str) or source.count(learned.BEG)!=1 or source.count(learned.END)!=1:
  raise ValueError("Learned policy block missing")
 if BEGIN in source or END in source:
  raise ValueError("Clarification already installed or unexpected markers")
 if TRIGGER not in {r["trigger"] for r in __import__("json").loads(__import__("base64").b64decode(
   __import__("re").search(r'sm_learned_rules=JSON.parse\(Base64.strict_decode64\("([^"]+)"\)\)',source).group(1)))}:
  raise ValueError("Unrecognized corrected buyer phrase")
 if any(source.count(x)!=1 for x in learned.PILOT):
  raise ValueError("Pilot boundary missing")
 return source.replace(learned.BEG,CODE+learned.BEG,1)

def expected_reply(source,rule):
 if rule["family"]!="extra_accessory" or rule["trigger"]!=TRIGGER:return None
 if BEGIN not in source and END not in source:return None
 if source.count(BEGIN)!=1 or source.count(END)!=1 or source.count(CODE)!=1:
  raise ValueError("Directness source drift")
 return REPLY
