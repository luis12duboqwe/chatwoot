# SoftMobile: Groq API in unrestricted development mode

The VPS operator has temporarily removed **application-level UTC daily limits for Groq API calls** while developing and testing the private Chatwoot pilot. This does **not** remove the limits imposed by Groq, nor enable customer-facing AI.

## Secure on/off switch

The Python module `groq_usage_policy.py` checks whether the local file `/etc/softmobile/groq-development-unlimited.enabled` exists, is owned by root, and is not writable by group or other users. While present, `request_cap(normal)` returns a practically non-binding limit (`sys.maxsize`). Removing that file restores configured limits on the **next service execution**. The normal limits are: synthetic shared pool 160/day, private bridge 30/day, objections evaluation 2 runs/day, quality auditor 12/day, patch proposer 4/day.

The daily limits are applied to API *consumption* only. Existing request payload caps, synthetic batch sizes, per-cycle bounds, safe validation, local model configuration, private notes only, Chatwoot pilot scope (account 2, inbox 2, conversation 3), permission checks, no uncontrolled code execution, backup/rollback and live-deployment limits stay in effect.

Groq can respond with HTTP 429 or another quota failure. **Do not rotate keys or create extra accounts to evade Groq's quotas.** Repeated scheduled jobs should not be mistaken for guaranteed available requests. If a paid Groq plan or billing is configured, increased API use may incur provider charges.

## Verification 2026-10-18 UTC

- Re-tested 242 offline Python tests in the VPS after enabling the root-owned switch; all passed.
- The shared synthetic API call counter advanced from 160 to 168 after a scheduled-lab-style run, demonstrating that the internal 160/day barrier is no longer active.
- Public Ruby bot remained byte-identical (SHA-256 `e1c5fd9d11754972b60257f906907d48e918b905584930e8adbbc3c57e55dacd`).
- Auto-promotion caps are **not** lifted: repair lab 1 promotion/day, bounded autofixer 2/day.

This is a reversible development configuration. Retain the private pilot and safety gates until independently reviewed and commercially verified.
