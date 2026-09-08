# Error and degradation policy

## Rule

The platform returns a bounded, correlated failure state when it cannot serve a
request safely. It never substitutes an estimate, stale success, or invented
metric for a failed operation.

| Condition | Class | Behaviour | Required evidence |
|---|---|---|---|
| Invalid API contract | client rejection | reject before routing; do not call a worker | request ID, validation reason |
| Colocated worker unavailable | serving failure | return bounded failure; no synthetic response | router ID, backend state, error class |
| Requested P/D path unavailable | availability degradation | fall back to colocated only when that route is healthy; otherwise fail | requested/selected route, fallback reason |
| Router timeout | serving failure | stop at timeout and return correlated failure | timeout value, route, error class |
| Cache/LMCache unavailable | performance degradation | recompute only on a documented healthy route | cache state, selected route, latency status |
| Required RAG index unavailable | grounded-answer failure | return insufficient-evidence failure; do not answer without retrieved sources | retrieval ID, index version, error class |
| Required RAG yields no authorized evidence | grounded-answer abstention | return insufficient-evidence state; do not invent citations | retrieval ID, knowledge-base version, retrieval count |
| MCP unavailable or invalid | agent failure | fail closed; no alternative tool or write action | task ID, tool ID, policy/error class |
| Duplicate tool retry | agent protection | honor idempotency key and do not repeat an action | task ID, idempotency key, disposition |
| Session state unavailable | agent failure | preserve no unsafe partial state; return failure | task ID, state-store error class |

`P/D -> colocated` is an inference-route fallback, not authorization to retry a
tool with broader privilege. Tool and agent failures always fail closed.

## Reporting rule

For every degraded request report: requested route, selected route, execution
mode, correlation IDs, whether the request completed, and which metric values
are `NA`. Do not describe a fallback as successful P/D execution.
