# Agent boundary

The agent is an optional, bounded operations interface; it is not the core
inference serving path. It may load durable session state, request inference,
and call an allowlisted read-only MCP tool. It must persist audit events and
fail closed on an unavailable tool, invalid input, authorization denial or
state-store failure.

The first implementation should reuse the behavioural contract of Lab 03:
one deterministic decision, one allowlisted read-only observation path, an
idempotency key, and explicit `completed`, `failed_closed`, or
`waiting_approval` state. No shell, filesystem write, secret reader, generic
command executor, or `pods/exec` capability belongs here.
