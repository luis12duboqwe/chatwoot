#!/usr/bin/env python3
"""Share provider HTTP429 retry-after hints across Groq background laboratories.

No credentials, model inputs or personal data are persisted. This is a
temporary provider-aware cooldown, NOT a reinstated daily token cap.
"""
import fcntl
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from quality_auditor import _atomic_json,_load

ROOT=Path(__file__).resolve().parent
STATE=ROOT/"quality"/"provider-cooldown.json"
LOCK=ROOT/"quality"/"provider-cooldown.lock"
MIN_DELAY=30
MAX_DELAY=900

def delay_seconds(headers,now=None):
 now=now or datetime.now(timezone.utc)
 raw=headers.get("Retry-After") if headers else None
 if raw is not None:
  try:
   v=int(str(raw).strip())
   return min(MAX_DELAY,max(MIN_DELAY,v))
  except (ValueError,TypeError):pass
  try:
   t=parsedate_to_datetime(str(raw))
   if t.tzinfo:return min(MAX_DELAY,max(MIN_DELAY,int((t.astimezone(timezone.utc)-now).total_seconds())))
  except (ValueError,TypeError,IndexError):pass
 return 90

def state_at(now=None):
 now=now or datetime.now(timezone.utc)
 data=_load(STATE,{})
 if not isinstance(data,dict):return 0
 t=data.get("until")
 if not isinstance(t,str):return 0
 try:limit=datetime.fromisoformat(t)
 except ValueError:return 0
 if not limit.tzinfo:return 0
 return max(0,int((limit.astimezone(timezone.utc)-now).total_seconds()))

def enforce(now=None):
 if state_at(now)>0:raise RuntimeError("Temporary Groq provider cooldown active")

def register_http_429(headers=None,now=None):
 now=now or datetime.now(timezone.utc)
 STATE.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 with open(LOCK,"a+") as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  d=delay_seconds(headers,now)
  until=now+timedelta(seconds=d)
  current=_load(STATE,{})
  try:
   last=datetime.fromisoformat(current.get("until",""))
   if last.tzinfo and last>until:until=last
  except (ValueError,TypeError,AttributeError):pass
  _atomic_json(STATE,{"until":until.isoformat(),"cause":"http_429_provider"})
  return int((until-now).total_seconds())
