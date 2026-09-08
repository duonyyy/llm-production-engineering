# Structured logging contract

Each terminal event records timestamp, severity, execution mode, component,
terminal status and opaque correlation IDs. It may include an error class,
route, metric availability state, knowledge-base/index version and bounded
counts. It must not include raw prompts, document text, chunks, access tokens,
authorization headers, secrets or full tool payloads.

The minimum lifecycle records are: request received, retrieval completed or
abstained, route selected, inference completed or failed, tool call requested
or denied, and response terminal state. Log rotation and retention policy must
be explicit before calling logs operational evidence.
