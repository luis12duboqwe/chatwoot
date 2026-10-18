# SoftMobile: autonomous conversation learning (pilot only)

## What is running

The existing synthetic and interactive Groq laboratories generate fictional buyer dialogues and store adjudicated issues. The hourly `softmobile-autonomous-learning.timer` picks an unhandled utterance only if a synthetic judge reports an error **and** a separate deterministic check confirms that the bot omitted a topic. It then requests an exact-match classification from Groq.

The model returns **data only**: a family label, the original exact buyer utterance, and a short explanation. No AI-authored Ruby, regular expressions, customer-facing prices, policies, or commands are executed.

The fixed compiler produces a small, exact-utterance human-handoff policy for four currently approved topics: express shipping costs, extra accessories, optional extended warranty, and tracking existing orders. It recognizes previously unseen buyer phrasings within those topics. It will not respond to messages containing sensitive details.

The policy is **pilot account 2, inbox 2, conversation 3 only**, with a maximum of one new auto-promotion per UTC day and at most eight rules. It does not remove limits from the existing automatic repair mechanisms or expand public client access.

## Required deployment gates

1. Source must exactly match the guarded pilot and have the test entry point.
2. Selection must match verbatim a verified fictional buyer turn and a permissible topic signature; unsafe phrases are rejected.
3. Ruby syntax is validated in an ephemeral container without networking, writable root, credentials, or production mounts.
4. Baseline and candidate are run in independent isolated Ruby processes on the exact scenario, with four unrelated negative controls. They must show a relevant improvement and a human handoff.
5. All seven isolated Ruby suites must pass: 57+5+7+20+11+2+15 = 117 tests.
6. The live bot timer is paused, a backup is created, candidate is atomically promoted, all tests are rerun, and automatic rollback occurs on test failure. The synthetic issue stays marked pending a future retest. No general release is performed.

## First verified deployment, 18 October 2026 (UTC)

- Source issue: `b735b499e02b3eea74`, fully synthetic Groq dialogue.
- The bot ignored a question about whether a funda could be added without extra cost, instead asking again for the model.
- The model selected `extra_accessory`; the fixed response explicitly requires an adviser to verify compatibility, whether the accessory is included, and price. It does not promise a free accessory.
- Targeted before/after: corrected, negative controls unchanged.
- 247/247 Python local tests; 117/117 Ruby isolated tests before promotion and 117/117 Ruby tests after promotion.
- Post-promotion Ruby SHA-256: `4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106`.
- Backup stored under `/opt/softmobile-waha-test/quality-backups`.
- Scheduled systemd service: `softmobile-autonomous-learning.service` with timer every hour at minute 43 UTC.

## Limits and next maturity stage

This is bounded automatic improvement, **not** general self-modifying software. The model cannot add brand-new categories, new pricing or warranty policies, or executable code without a separate reviewed software change. Exact triggers do not yet generalize broadly to paraphrases. Real inventory, financing terms and sales outcomes require authoritative data. The independent AI grader can be wrong; these tests are necessary but do not prove customer satisfaction.

To inspect: `python3 autonomous_learning.py --status`. To pause: `systemctl disable --now softmobile-autonomous-learning.timer`. To switch back on: `systemctl enable --now softmobile-autonomous-learning.timer`. The existing Groq development-usage switch is separate from this promotion control.
