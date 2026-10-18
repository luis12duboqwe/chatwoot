# SoftMobile | Autonomous-learning maturity gates | 2026-10-18

These features run **only** in the previously authorized pilot (Chatwoot account 2,
inbox 2, conversation 3), not across customer accounts.

## Phase 1: Evidence-based synthetic triage — implemented

`issue_triage.py` groups fictional cases by validity, AI-only suspicion,
deterministic signal, signal agreement, installed rule pending retest, or
verified-independent retest. It does not mark synthetic findings as proven
real-customer errors. The service/timer `softmobile-issue-triage` refreshes
the private report on a schedule.

At the first check: 88 records, 17 convergent pending replay, 19
deterministic-only pending replay, 37 AI-only unverified, 9 AI-cleared needing
deterministic review, 2 deployed needing retest, 4 invalid. There were no
identical full-dialogue duplicates by canonical fingerprint.

## Phase 2: Generalize only approved families — staged

`semantic_generalization.py` produces **static-reviewed** Ruby for the
accessory inclusion/price family already approved by a fictional issue and
a previously deployed exact-utterance rule. The model cannot write Ruby,
regular expressions, policy text or prices. The new rule requires both
accessory and pricing/inclusion cues, denies after-sales/security/payment
contexts, and escalates to a human without confirming stock or cost.

The candidate passed 10/10 distinct positive paraphrases, left 14/14
negative scenarios unchanged, and passed 117/117 isolated Ruby regressions.
It is an INERT stage file until its promotion separately succeeds. Future
learning preserves the exact audited static code; unexpected source drift
fails closed.

`semantic_promoter.py` independently checks current source hash, staged
candidate hash, daily promotion cap, before/after and negative suites,
isolated Ruby regressions, and then uses the existing backed-up atomic
deployment/rollback procedure. A separate scheduled service runs after
UTC rollover at 00:17; today the service correctly reported
`daily_deployment_cap`, leaving the existing Ruby unchanged. A successful
future scheduled run is not promised; inspect evidence.

## Phase 3: Code proposals remain segregated

The Groq `patch_proposer.py` path already requests untrusted Ruby
suggestions only in an allowlisted context block, validates them inside a
disposable no-network container, and stages them for human review. It does
not authorize unconstrained AI-written code to be executed in production.
Enabling arbitrary automatic code modification is intentionally not a
condition for considering the safe pilot functional.

## Phase 4: Post-deploy evaluation and provider backoff — implemented

`learned_retest.py` performs independent no-network deterministic replays
and optionally asks Groq for a second opinion; it clearly distinguishes
local passing from AI confirmation. `provider_cooldown.py` responds to
Groq HTTP 429 using Retry-After (30 to 900 seconds) or a conservative
90-second fallback. It writes no keys, private messages or model inputs
and is NOT a new daily usage limit. Pending Groq verdicts are not counted
as AI-approved responses.

## Phase 5: Sale readiness — blocked by missing verified data

`production_readiness.py` fails closed; it NEVER enables global messaging
or payments itself. The accessible Google Drive *CATÁLOGO MAESTRO -
SOFTMOBILE* showed 97 catalogued variants, 46 unique models and **0 with
stock loaded** at inspection. The list's prices are sale-list values,
not confirmed per-unit live prices. Colors, condition, shipping, financing,
warranties and reservation commitments still require verified authoritative
sources and explicit owner approval. The existing Ruby pilot also explicitly
keeps `inventory=[]` in its Chatwoot path.

Before retail rollout: connect actual approved ally/ERP inventory,
synchronize model/capacity/color/IMEI-level availability and reliable
prices, validate real messages and checkout handoff with human supervision,
and obtain separate explicit authorization for broader customer scope.

## Verifiable controls

- All Python regressions: `python3 -m unittest discover -p 'test_*.py' -q`
- Isolated Ruby: `isolated_gate.py` suite inside disposable no-network container.
- Synthetic triage: `python3 issue_triage.py`
- Semantic candidate: `python3 semantic_generalization.py`
- Promotion status: `python3 semantic_promoter.py --status`
- Latest learned-rule verdict: `python3 learned_retest.py --status`
- Production readiness: `python3 production_readiness.py`
- Stop all automated semantic promotion: `systemctl disable --now softmobile-semantic-promotion.timer`
- The underlying Groq development-unlimited switch and account/token quotas
  remain separate from safe deployment limits and from HTTP429 retries.

Do not label this system a self-programming unrestricted AI. The available
autonomy is evidence-gated, allowlisted, pilot-restricted, and reversible.
