#!/usr/bin/env python3
"""Read-only observation of Chatwoot -> WAHA pilot transport, no message sends.

A Chatwoot message with status sent is not proof of handset delivery.
Reports safe metadata for conversation #3; never exports identifiers or content.
"""
import argparse
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from urllib import request, error

from quality_auditor import DATA, _atomic_json, _load

REPORT = DATA / "e2e-transport.json"
MARK = "SM_E2E_JSON="
DOCKER = "softmobile-chatwoot-rails-1"
WAHA = "softmobile-waha-test-waha-1"
WAHA_URL = "http://127.0.0.1:3201/api/sessions"
STALE_AFTER_SECS = 600

def rails_snapshot(runner=subprocess.run):
    # READ ONLY: no ORM writes, no customer content/identifiers returned.
    ruby = rf"""require 'json'
c=Conversation.find_by(id:3)
raise 'pilot scope invalid' unless c && c.account_id==2 && c.inbox_id==2
last=c.messages.where(message_type: :incoming,private: false).reorder(id: :desc).first
public=c.messages.where(message_type: :outgoing,private:false)
bot=public.where("content_attributes::text LIKE ?",'%softmobile_source_message_id%')
latest=bot.reorder(id: :desc).first
kind='none'
if last
  plain=last.content.to_s.unicode_normalize(:nfkd).gsub(/\p{{Mn}}/,'').downcase.strip.gsub(/[.!?¿¡ ]+\z/,'')
  kind=if last.attachments.exists? then 'media'
    elsif %w[ok listo gracias si entendido vale perfecto hola].include?(plain)
      'ack'
    elsif %w[efectivo transferencia transferencias tarjeta galerias retiro].include?(plain)
      'short_choice'
    elsif plain.include?('?') || plain.match?(/\b(?:tienen|cuanto|precio|disponible|busco|quiero)\b/)
      'question_or_purchase'
    else 'other' end
end
bot_for_latest=nil
manual_after=nil
if last
  bot_for_latest=bot.where("content_attributes::text LIKE ?",'%softmobile_source_message_id%').detect do |m|
    m.content_attributes.is_a?(Hash) && m.content_attributes['softmobile_source_message_id'].to_s==last.id.to_s
  end
  manual_after=public.where('created_at > ?',last.created_at).where.not(id: bot.pluck(:id)).exists?
end
statuses=public.reorder(nil).group(:status).count.transform_keys(&:to_s)
puts '{MARK}' + {{
 account_id:c.account_id,inbox_id:c.inbox_id,
 incoming_total:c.messages.where(message_type: :incoming,private:false).count,
 public_total:public.count, bot_total:bot.count,
 public_status_counts:statuses, latest_incoming_id:(last&.id || 0),
 latest_incoming_at:(last&.created_at&.utc&.iso8601),
 latest_incoming_kind:kind,
 latest_bot_id:(latest&.id || 0),
 latest_bot_status:latest&.status,
 latest_bot_for_incoming:!bot_for_latest.nil?,
 latest_bot_response_status:bot_for_latest&.status,
 manual_reply_after_last_incoming:!!manual_after
}}.to_json
"""
    result = runner(["docker", "exec", "-i", DOCKER, "sh", "-lc",
                     "RAILS_ENV=production bundle exec rails runner -"],
                    input=ruby, text=True, capture_output=True, timeout=45, check=False)
    if result.returncode:
        raise RuntimeError("Pilot Chatwoot read failed")
    for line in result.stdout.splitlines():
        if line.startswith(MARK):
            obj = json.loads(line[len(MARK):])
            if obj.get("account_id") != 2 or obj.get("inbox_id") != 2:
                raise RuntimeError("Scope changed")
            return obj
    raise RuntimeError("Pilot read gave no data")

def waha_status(runner=subprocess.run, opener=request.urlopen):
    # Read container environment in memory only. Never print API key or session identifier.
    p=runner(["docker","inspect",WAHA],text=True,capture_output=True,timeout=12,check=False)
    if p.returncode:raise RuntimeError("WAHA not available")
    payload=json.loads(p.stdout)[0]
    env=dict(v.split("=",1) for v in payload.get("Config",{}).get("Env",[]) if "=" in v)
    key=env.get("WAHA_API_KEY_PLAIN") or env.get("WAHA_API_KEY")
    if not key:raise RuntimeError("WAHA key unavailable")
    req=request.Request(WAHA_URL,headers={"X-Api-Key":key, "User-Agent":"SoftMobile-Pilot-Transport-Monitor/1.0"})
    try:
        with opener(req,timeout=10) as res:
            if res.status!=200:raise RuntimeError("WAHA API unavailable")
            result=json.loads(res.read(12000))
    except (error.HTTPError,error.URLError,TimeoutError,ValueError) as exc:
        raise RuntimeError("WAHA API unavailable") from exc
    if not isinstance(result,list):
        raise RuntimeError("WAHA session response malformed")
    # Only session statuses leave this function, no phone numbers, session ids or keys.
    states=[x.get("status","UNKNOWN") for x in result if isinstance(x,dict)]
    return {"session_count":len(states),"working":states.count("WORKING"),
            "all_working":bool(states) and all(x=="WORKING" for x in states)}

def classify(snapshot,transport,at=None):
    at=at or datetime.now(timezone.utc)
    if not transport.get("all_working"):
        return "transport_unhealthy"
    if snapshot.get("latest_incoming_id",0)<=0:
        return "no_customer_history"
    raw=snapshot.get("latest_incoming_at")
    if not raw:return "unknown"
    t=datetime.fromisoformat(raw.replace("Z","+00:00"))
    age=max(0,(at-t).total_seconds())
    if snapshot.get("latest_bot_for_incoming"):
        # No claim of WhatsApp handset delivery; Chatwoot message is merely 'sent'.
        return "chatwoot_bot_reply_recorded"
    if snapshot.get("manual_reply_after_last_incoming"):
        return "human_reply_recorded"
    if snapshot.get("latest_incoming_kind")=="ack":
        return "ack_no_public_reply_expected"
    if age < STALE_AFTER_SECS:
        return "pending_recent_inbound"
    # Some intents intentionally do not trigger a public message.
    return "unanswered_inbound_needs_review"

def run():
    snap=rails_snapshot()
    transport=waha_status()
    status=classify(snap,transport)
    result={
      "pilot_conversation":3,
      "time":datetime.now(timezone.utc).isoformat(),
      "status":status,
      "chatwoot":{"incoming_total":snap["incoming_total"],"public_outgoing_total":snap["public_total"],
        "bot_outgoing_total":snap["bot_total"],"public_status_counts":snap["public_status_counts"],
        "last_incoming_id":snap["latest_incoming_id"],
        "last_incoming_kind":snap["latest_incoming_kind"],
        "bot_reply_for_last_incoming":snap["latest_bot_for_incoming"],
        "human_reply_for_last_incoming":snap["manual_reply_after_last_incoming"]},
      "waha":transport,
      "physical_phone_delivery_verified":False,
      "notes":"Metadata only; Chatwoot sent status is not WhatsApp delivered/read receipt"
    }
    _atomic_json(REPORT,result)
    return result

def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run",action="store_true")
    modes.add_argument("--status",action="store_true")
    args=parser.parse_args()
    if args.status:
        print(json.dumps(_load(REPORT,{"status":"no_observation_yet"}),ensure_ascii=False))
        return 0
    try:
        result=run()
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (RuntimeError,ValueError,OSError,KeyError):
        print("pilot_transport_observation_failed_safely")
        return 2

if __name__=="__main__":
    raise SystemExit(main())
