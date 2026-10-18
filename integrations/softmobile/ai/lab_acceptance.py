#!/usr/bin/env python3
"""Evidence-based status of SoftMobile autonomous lab, NOT sales approval.

100 means the *lab acceptance checklist* is met by observed evidence.
It does not guarantee that the model is infallible or authorize public sales.
All paths are local; no Groq, real stock, messages, code deployment or writes
except the isolated quality status report. Missing data fails closed.
"""
import argparse,hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from quality_auditor import _load,_atomic_json

BASE=Path(__file__).resolve().parent
QA=BASE/"quality"
RESULT=QA/"lab-acceptance-report.json"
CURRENT_RUBY=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
KNOWN_CATEGORIES={"changes","checkout","shipping","payments","questions","objections","cancellation","financing","security","trust"}

def recent(value,hours,now=None):
 now=now or datetime.now(timezone.utc)
 if not isinstance(value,str):return False
 try:
  dt=datetime.fromisoformat(value)
  return bool(dt.tzinfo and 0<=(now-dt.astimezone(timezone.utc)).total_seconds()<=hours*3600)
 except (TypeError,ValueError):return False

def gauge(name,points,pass_,details):
 return {"name":name,"possible":points,"earned":points if pass_ else 0,
         "passed":bool(pass_),"details":details}

def calculate(load=_load,active_ruby=None,now=None):
 now=now or datetime.now(timezone.utc)
 obj=lambda filename,default={}:load(QA/filename,default)
 synth=obj("synthetic-lab-state.json")
 summ=obj("synthetic-lab-summary.json")
 inter=obj("interactive-lab-transcripts.json",[])
 deferred=obj("deferred-grading-report.json")
 replay=obj("offline-issue-replay-report.json")
 triage=obj("issue-triage-report.json")
 queue=obj("issue-resolution-queue.json")
 sales=obj("sales-conversion-training-report.json")
 hold=obj("financing-holdout-report.json")
 stock=obj("training-inventory-quality-report.json")
 candidate=obj("combined-pilot-review.json")
 independent=obj("directness-independent-review.json")
 learned=obj("learned-dialogue-retest.json")
 production=obj("production-readiness.json")
 if not isinstance(inter,list):inter=[]
 graded=sum(isinstance(x,dict) and x.get("grade") is not None for x in inter)
 all_replies=len(inter)
 categories={x.get("category") for x in inter if isinstance(x,dict) and x.get("category") in KNOWN_CATEGORIES}
 evidence=candidate.get("gates",{}) if isinstance(candidate,dict) else {}
 differential=replay.get("differential",{}) if isinstance(replay,dict) else {}
 digest=hashlib.sha256(active_ruby.encode()).hexdigest() if isinstance(active_ruby,str) else (
      hashlib.sha256(CURRENT_RUBY.read_bytes()).hexdigest() if CURRENT_RUBY.is_file() else None)
 qa_review_pending=sum(n for name,n in triage.get("bucket_counts",{}).items()
                       if name in ("convergent_signals_pending_replay",
                                  "deterministic_signal_pending_replay","deployed_needs_retest")
                       and isinstance(n,int))
 checks=[
  gauge("generacion_sintetica",10,
        synth.get("scenarios",0)>=200 and recent(summ.get("at"),2,now),
        {"simulated_conversations":synth.get("scenarios",0),"recent":recent(summ.get("at"),2,now)}),
  gauge("compradores_interactivos",5,
        all_replies>=10 and len(categories)>=8 and recent(obj("interactive-lab-summary.json").get("at"),2,now),
        {"conversations":all_replies,"categories":len(categories)}),
  gauge("evaluaciones_independientes",10,
        all_replies>=10 and graded/all_replies>=.95 and recent(deferred.get("at"),1,now),
        {"graded":graded,"total":all_replies,"coverage":round(graded/max(1,all_replies),4),
         "pending":all_replies-graded}),
  gauge("reproduccion_sin_red",10,
        replay.get("replayed",0)>=100 and replay.get("api_calls")==0
        and recent(replay.get("at"),1,now),
        {"replayed":replay.get("replayed",0),
         "no_api_calls":replay.get("api_calls")==0}),
  gauge("clasificacion_de_incidentes",10,
        recent(triage.get("at"),2,now) and triage.get("total_records",0)>=100
        and triage.get("promoted_or_proven_by_ai_alone")==0,
        {"classified":triage.get("total_records",0),"signals_needing_replay":qa_review_pending}),
  gauge("cierre_de_senales_reproducidas",10,
        recent(queue.get("at"),2,now)
        and queue.get("unreviewed_clusters")==0
        and queue.get("real_customer_defects_proven")==0,
        {"clusters_awaiting_independent_review":queue.get("unreviewed_clusters"),
         "reproduced_hypotheses":queue.get("reviewable_replayed_hypotheses")}),
  gauge("candidata_probada_sin_regresiones",10,
        candidate.get("status")=="verified_staged"
        and evidence.get("status")=="gates_passed"
        and evidence.get("sales_after")==72 and evidence.get("holdout_after")==48
        and evidence.get("stock_after")==108
        and evidence.get("ruby_regressions",0)>=117
        and evidence.get("semantic_negative",0)>=15
        and evidence.get("synthetic_backlog_new_flags")==0
        and independent.get("status")=="independent_ai_approved"
        and independent.get("candidate_sha256")==candidate.get("candidate_sha256")
        and recent(independent.get("at"),24,now),
        {"sales":evidence.get("sales_after"),"holdout":evidence.get("holdout_after"),
         "stock":evidence.get("stock_after"),"previous_cases":evidence.get("synthetic_backlog_replayed"),
         "new_flags":evidence.get("synthetic_backlog_new_flags"),
         "ai_review":independent.get("status")}),
  gauge("version_instalada_aprueba_ventas",15,
        digest is not None and digest==candidate.get("candidate_sha256")
        and sales.get("passed")==72 and hold.get("passed")==48
        and sales.get("scenarios")==72 and hold.get("total")==48
        and recent(sales.get("at"),2,now) and recent(hold.get("at"),2,now),
        {"live_sha":digest,"candidate_sha":candidate.get("candidate_sha256"),
         "live_sales_passed":sales.get("passed"),"live_financing_passed":hold.get("passed")}),
  gauge("postinstalacion_y_segunda_opinion",10,
        digest is not None and digest==candidate.get("candidate_sha256")
        and learned.get("deterministic_failed")==0
        and learned.get("ai_flagged")==0
        and learned.get("ai_confirmed",0)>=learned.get("checked",1)
        and recent(learned.get("at"),4,now),
        {"retest_status":learned.get("status"),"ai_confirmed":learned.get("ai_confirmed")}),
  gauge("aislamiento_del_piloto",5,
        production.get("pilot_scope_verified") is True
        and production.get("global_customer_rollout_authorized") is False
        and production.get("orders_or_payments_authorized") is False
        and replay.get("public_messages_sent")==0
        and replay.get("real_inventory_changed") is False,
        {"pilot_limited":production.get("pilot_scope_verified"),
         "public_rollout_authorized":production.get("global_customer_rollout_authorized")}),
  gauge("devolucion_y_limite_de_cambios",5,
        candidate.get("pilot_only") is True
        and candidate.get("arbitrary_llm_code_executed") is False
        and replay.get("no_auto_promotion") is True
        and (QA/"learned-dialogue-history.json").is_file(),
        {"no_unbounded_code":candidate.get("arbitrary_llm_code_executed") is False,
         "replay_may_deploy":not bool(replay.get("no_auto_promotion"))})
 ]
 total=sum(x["earned"] for x in checks)
 result={"at":now.isoformat(),"category":"TECHNICAL_LAB_ACCEPTANCE_ONLY",
         "weighted_score_percent":total,
         "possible_percent":100,"complete":total==100,
         "checks":checks,"open_criteria":[x["name"] for x in checks if not x["passed"]],
         "unresolved_qa_signals":qa_review_pending,
         "historical_qa_alerts_are_not_confirmed_customer_defects":True,
         "cannot_authorize_public_rollout":True,
         "real_inventory_verified":production.get("verified_inventory_evidence") is True,
         "public_messages_sent":0,
         "note":"This acceptance test does not claim AI infallibility or authorize real sales."}
 assert sum(x["possible"] for x in checks)==100
 return result

def main():
 p=argparse.ArgumentParser()
 group=p.add_mutually_exclusive_group(required=True)
 group.add_argument("--run",action="store_true")
 group.add_argument("--status",action="store_true")
 a=p.parse_args()
 if a.status:print(json.dumps(_load(RESULT,{"status":"not_run"}),ensure_ascii=False));return 0
 try:
  result=calculate()
  _atomic_json(RESULT,result)
  print(json.dumps({k:v for k,v in result.items() if k!="checks"},ensure_ascii=False))
  return 0
 except (RuntimeError,ValueError,TypeError,KeyError,OSError):
  print("lab_acceptance_failed_closed");return 2

if __name__=="__main__":sys.exit(main())
