# Router boundary

The router accepts the API contract, preserves `X-Request-ID`, selects
`colocated` or `pd`, records the selected route, and applies the error policy.
It must not log raw prompts or authorization headers.

Local implementation starts with `colocated`. The `pd` route remains a
reference-only path until a Linux environment with two compatible GPUs and
transfer telemetry is available. A future implementation should adapt the
Lab 03 router contract rather than duplicate its source without review.
