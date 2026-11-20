# Hermes smart-approval verdict parser fix (2026-11-07)

Symptom: `Timeout - denying command` plus duplicated replies.

Root cause: the relay returned repeated verdict tokens (`APPROVEAPPROVE`,
`OKOK`, duplicated JSON). `tools/approval.py` compared the auxiliary model's
answer with an exact string equality (`answer == "APPROVE"`), so every
duplicated verdict fell through to `escalate`, and with no human present the
hard-deny timer fired after ~305 s.

Fix: tolerant verdict parsing collapses repeated tokens to a single
APPROVE / DENY / ESCALATE before dispatch; approval timeout raised 300 -> 600 s;
denial breaker 3 -> 5; the approval auxiliary model moved to a purely local
Ollama endpoint so no external relay or proxy is involved. A `patch_approval_parse.py`
re-applies the patch idempotently after `hermes update`.

This document intentionally contains NO config.yaml / .env fragments: those files
hold gateway keys and private addresses and are excluded from publication.
