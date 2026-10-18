#!/usr/bin/env python3
"""Global one-per-UTC-day cap shared by the independent SoftMobile repair labs.

The callers already hold the common autofix.lock when evaluating/writing
deployment records, so the count is consistent across their deployment
paths. No provider/token/cost quota is imposed by this safety guard.

Each successful deployment is counted ONCE via its owning event log. Events
whose deployment status is unknown do not grant permission to deploy.
"""
from datetime import date,datetime,timezone
from pathlib import Path
import re
from quality_auditor import _load

ROOT=Path(__file__).resolve().parent/"quality"
DAILY_LIMIT=1
SOURCES={
 "payment_autofix":"autofix-history.json",
 "repair_family":"repair-lab-history.json",
 "learned_and_semantic":"learned-dialogue-history.json",
}

def active_day(now=None):
 now=now or datetime.now(timezone.utc)
 if now.tzinfo is None:raise ValueError("Timezone required")
 return now.astimezone(timezone.utc).date().isoformat()

def counted(row,source):
 if source=="payment_autofix":
  return row.get("status")=="deployed"
 return row.get("promoted") is True

def usage(day=None,loader=_load,root=None):
 day=day or active_day()
 if not isinstance(day,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day):
  raise ValueError("Invalid UTC date")
 try:date.fromisoformat(day)
 except ValueError as ex:raise ValueError("Invalid UTC date") from ex
 root=ROOT if root is None else Path(root)
 counts={}
 for source,file in SOURCES.items():
  rows=loader(root/file,[])
  if not isinstance(rows,list):raise ValueError("Unsafe promotion log "+source)
  count=0
  for row in rows:
   if not isinstance(row,dict):raise ValueError("Invalid promotion record "+source)
   if not counted(row,source):continue
   stamp=row.get("day")
   if not isinstance(stamp,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",stamp):
    raise ValueError("Undated promotion record "+source)
   if stamp==day:count+=1
  counts[source]=count
 return {"day":day,"limit":DAILY_LIMIT,"by_source":counts,
         "total":sum(counts.values()),"available":sum(counts.values())<DAILY_LIMIT}

def exhausted(day=None):
 return not usage(day)["available"]
