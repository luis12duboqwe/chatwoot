#!/usr/bin/env python3
"""Fail-closed SoftMobile rollout readiness based on verified local evidence.

The upstream Google Sheet price catalog is a *reference*, not proof of live
inventory, color, price freshness, or fulfilled orders. This gate cannot enable
global customer messaging or authorize a sale by itself.
"""
import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path

from quality_auditor import _atomic_json,_load
import autonomous_learning as learn

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"quality"
REPORT=DATA/"production-readiness.json"
SOURCE=DATA/"catalog-source-evidence.json"
SECRET=ROOT/"../sales-bot-v2.rb"
STALE_MINUTES=20
REQUIRED_FIELDS={"source","checked_at","items","verified_units","verified_prices",
                 "verified_colors","approved_by_operator"}
PUBLIC_SOURCE_ID="softmobile-google-catalog-read-only"

def _date(s):
 try:
  d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
  if d.utcoffset() is None:return None
  return d.astimezone(timezone.utc)
 except (ValueError,TypeError,OverflowError):return None

def validate_stock_evidence(evidence,now=None):
 """A source spreadsheet alone is NEVER sufficient to sell known inventory."""
 now=now or datetime.now(timezone.utc)
 if not isinstance(evidence,dict) or set(evidence)!=REQUIRED_FIELDS:
  return False,"missing_or_invalid_evidence"
 if evidence["source"]!=PUBLIC_SOURCE_ID:return False,"untrusted_source"
 verified=[evidence[k] for k in ("items","verified_units","verified_prices","verified_colors")]
 if any(type(x) is not int or x<0 for x in verified):return False,"invalid_counts"
 if evidence["verified_units"]<1 or evidence["verified_prices"]<1 or evidence["verified_colors"]<1:
  return False,"missing_stock_or_pricing"
 if any(x>evidence["items"] for x in verified):return False,"inconsistent_catalog_counts"
 if evidence["approved_by_operator"] is not True:return False,"operator_approval_required"
 stamp=_date(evidence["checked_at"])
 if stamp is None or stamp>now or now-stamp>timedelta(minutes=STALE_MINUTES):
  return False,"stale_or_invalid_verification"
 return True,"evidence_recent_and_approved"

def evaluate(evidence=None):
 live=learn.BOT.read_text()
 stock=evidence if evidence is not None else _load(SOURCE,{})
 safe_scope=all(live.count(s)==1 for s in learn.PILOT)
 ok,reason=validate_stock_evidence(stock)
 # This gate does not enable launch even when everything passes.
 return {
  "at":datetime.now(timezone.utc).isoformat(),
  "pilot_scope_verified":safe_scope,
  "verified_inventory_evidence":ok,
  "inventory_reason":reason,
  "source_note":"Drive catalog of 97 variants has zero loaded stock; price list values not real-time sale confirmations.",
  "global_customer_rollout_authorized":False,
  "live_price_quote_allowed":False,
  "live_stock_commitment_allowed":False,
  "orders_or_payments_authorized":False,
  "required_before_sales":["authoritative per-unit live stock","fresh verified price and color",
     "delivery/store ownership verification","human-approved warranty and financing policies",
     "real pilot customer journey and escalation test","explicit rollout approval"],
  "current_bot_sha256":hashlib.sha256(live.encode()).hexdigest()
 }

def run():
 r=evaluate();_atomic_json(REPORT,r);return r

if __name__=="__main__":
 print(json.dumps(run(),ensure_ascii=False))
