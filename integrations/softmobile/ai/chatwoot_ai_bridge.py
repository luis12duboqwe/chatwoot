#!/usr/bin/env python3
"""Groq -> Chatwoot private suggestions only, restricted to SoftMobile pilot #3.

No public messages, no channel send, no inventory mutation, no credentials in repo.
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from configurar_clave_groq import stored_key
from groq_pilot import PilotError, prepare, suggest

ROOT = Path(__file__).resolve().parent
STATE = ROOT / ".pilot_bridge_state.json"
CONV_ID = 3
ACCOUNT_ID = 2
INBOX_ID = 2
MAX_DAILY_REQUESTS = 30
DOCKER_NAME = "softmobile-chatwoot-rails-1"
PREFIX = "SM_AI_PRIVATE_NOTE_JSON="
PERSONAL = re.compile(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://\S+|"
                      r"(?<!\d)(?:\+?504[\s-]?)?[2-9]\d{3}[\s-]?\d{4}(?!\d)|"
                      r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)|"
                      r"\b(?:contrase[ñn]a|clave bancaria|c[oó]digo de verificaci[oó]n|"
                      r"identidad|pasaporte|pin|otp|cvv|direcci[oó]n exacta)\b)", re.I)

def rails_run(program, runner=subprocess.run):
    completed = runner(
        ["docker", "exec", "-i", DOCKER_NAME, "sh", "-lc",
         "RAILS_ENV=production bundle exec rails runner -"],
        input=program, text=True, capture_output=True, timeout=45, check=False)
    if completed.returncode != 0:
        raise RuntimeError("Chatwoot runner returned error; bot active unaffected.")
    for line in completed.stdout.splitlines():
        if line.startswith(PREFIX):
            return json.loads(line[len(PREFIX):])
    raise RuntimeError("Chatwoot runner returned no structured result.")

def get_next(after_id):
    after_id = int(after_id)
    if after_id < 0:
        raise ValueError("Invalid cursor")
    program = f"""require 'json'
c=Conversation.find_by(id:{CONV_ID})
raise 'unexpected account/inbox' unless c && c.account_id=={ACCOUNT_ID} && c.inbox_id=={INBOX_ID}
m=c.messages.where(message_type: :incoming, private: false).where('id > ?', {after_id}).reorder(id: :desc).first
puts '{PREFIX}' + (m ? {{id:m.id, content:m.content.to_s[0,1000], age_seconds:(Time.now.utc-m.created_at).to_i, has_attachments:m.attachments.exists?}} : {{id:nil}}).to_json
"""
    return rails_run(program)

def latest_id():
    program = f"""require 'json'
c=Conversation.find_by(id:{CONV_ID})
raise 'unexpected account/inbox' unless c && c.account_id=={ACCOUNT_ID} && c.inbox_id=={INBOX_ID}
last_id=c.messages.where(message_type: :incoming, private: false).maximum(:id) || 0
puts '{PREFIX}' + {{id:last_id}}.to_json
"""
    return int(rails_run(program)["id"])

def safe_text(raw):
    if not isinstance(raw, str) or not 4 <= len(raw) <= 600 or PERSONAL.search(raw):
        return None
    # Short acknowledgments are not useful for an isolated AI suggestion.
    if raw.strip().casefold().strip(" .!?¿¡").lower() in {
        "hola", "buenas", "ok", "okay", "listo", "sí", "si", "gracias",
        "efectivo", "tarjeta", "envío", "envio", "retiro", "negro", "azul",
        "morado", "transferencia", "galerías", "galerias"
    }:
        return None
    return raw

def put_private(marker, note):
    if not re.fullmatch(r"(?:DEMO-1|[1-9][0-9]{0,13})", marker):
        raise ValueError("Invalid message marker")
    if not isinstance(note, str) or not 30 <= len(note) <= 1500:
        raise ValueError("Invalid note")
    b64 = base64.b64encode(note.encode("utf-8")).decode("ascii")
    marker_b64 = base64.b64encode(marker.encode("ascii")).decode("ascii")
    message_check = "true" if marker == "DEMO-1" else "false"
    program = f"""require 'json'
require 'base64'
c=Conversation.find_by(id:{CONV_ID})
raise 'unexpected account/inbox' unless c && c.account_id=={ACCOUNT_ID} && c.inbox_id=={INBOX_ID}
token=Base64.strict_decode64('{marker_b64}')
body=Base64.strict_decode64('{b64}')
raise 'invalid body' unless body.start_with?("[SMAI:#{'{'}token{'}'}]") && body.bytesize < 3000
if {message_check} == false
  inbound=c.messages.where(message_type: :incoming,private:false)
  raise 'invalid inbound' unless inbound.where(id:token.to_i).exists?
  raise 'superseded inbound' unless inbound.maximum(:id)==token.to_i
end
scope=c.messages.where(private:true).where('content LIKE ?',"%[SMAI:#{'{'}token{'}'}]%")
if scope.exists?
  puts '{PREFIX}' + {{status:'duplicate',private:true}}.to_json
else
  Messages::MessageBuilder.new(nil,c,{{content:body,private:true}}).perform
  confirmed=scope.order(id: :desc).first
  raise 'private note not persisted' unless confirmed && confirmed.private? && confirmed.message_type=='outgoing'
  puts '{PREFIX}' + {{status:'created',private:true}}.to_json
end
"""
    result = rails_run(program)
    if not result.get("private") or result.get("status") not in ("created", "duplicate"):
        raise RuntimeError("Private note validation failed.")
    return result["status"]

def load_state():
    if not STATE.exists():
        raise RuntimeError("Not initialized; run --init to exclude historical messages.")
    st = STATE.stat()
    if st.st_mode & 0o077:
        raise RuntimeError("Insecure bridge state file permissions.")
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if data.get("pilot") != CONV_ID or type(data.get("after_id")) is not int:
        raise RuntimeError("Invalid bridge state.")
    return data

def save_state(data):
    parent = STATE.parent
    os.makedirs(parent, exist_ok=True)
    fd, dest = tempfile.mkstemp(dir=parent, prefix=".pilot-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(dest, 0o600)
        os.replace(dest, STATE)
    finally:
        if os.path.exists(dest):
            os.unlink(dest)

def format_note(marker, output):
    reply = output["suggested_reply"].replace("\n", " ").strip()
    return (
        f"[SMAI:{marker}] SUGERENCIA INTERNA DE IA — NO ENVIADA AL CLIENTE\n"
        f"Propuesta: {reply}\n"
        f"Revisión humana: {'SÍ' if output['human_review'] else 'recomendada'}\n"
        "No confirma stock, precio, financiación, garantía, reserva ni envío. "
        "Antes de usar, comprobar los datos comerciales con el responsable."
    )

def run_once():
    if os.getenv("SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED") != "true":
        raise RuntimeError("Bridge not enabled. No notes created.")
    state = load_state()
    today = datetime.now(timezone.utc).date().isoformat()
    if state.get("day") != today:
        state["day"], state["calls"] = today, 0
    if state.get("calls", 0) >= MAX_DAILY_REQUESTS:
        return "daily_limit"
    msg = get_next(state["after_id"])
    if msg["id"] is None:
        return "no_new_messages"
    ident = int(msg["id"])
    age = msg.get("age_seconds")
    if type(age) is not int or age < 0 or age > 390:
        state["after_id"] = ident
        save_state(state)
        return "skipped_stale"
    if msg.get("has_attachments") or not safe_text(msg.get("content", "")):
        state["after_id"] = ident
        save_state(state)
        return "skipped_sensitive_or_multimedia"
    state["calls"] = state.get("calls", 0) + 1
    save_state(state)  # Count before API to bound worst-case expenditure.
    try:
        clean = prepare({"conversation_id": CONV_ID, "message": msg["content"]})
        output = suggest(clean, stored_key())
        result = put_private(str(ident), format_note(str(ident), output))
        state["after_id"] = ident
        save_state(state)
        return "private_note_" + result
    except (PilotError, RuntimeError, ValueError):
        # Preserve after_id so a transient API error may be retried later,
        # while daily calls still cap requests.
        return "safe_fallback"

def demo_note():
    if os.getenv("SOFTMOBILE_CHATWOOT_AI_NOTES_ENABLED") != "true":
        raise RuntimeError("Bridge not enabled. No notes created.")
    sample = prepare({"conversation_id": CONV_ID,
                      "message": "Quisiera conocer un Samsung S22 Ultra de 256 GB."})
    output = suggest(sample, stored_key())
    return "demo_" + put_private("DEMO-1", format_note("DEMO-1", output))

def main():
    p = argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--init",action="store_true")
    group.add_argument("--once",action="store_true")
    group.add_argument("--demo-note",action="store_true")
    args=p.parse_args()
    try:
        if args.init:
            if STATE.exists():
                raise RuntimeError("Already initialized; refusing to reset cursor.")
            save_state({"pilot":CONV_ID,"after_id":latest_id(),"day":"","calls":0})
            print("initialized_at_latest_incoming")
        elif args.demo_note:
            print(demo_note())
        else:
            print(run_once())
    except Exception as err:
        print("safe_error:" + type(err).__name__)
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
