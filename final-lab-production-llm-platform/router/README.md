# Router boundary

The core router accepts the API contract, preserves `X-Request-ID`, selects the
`colocated` route, records the selected route, and applies the error policy. It
must not log raw prompts or authorization headers.

The `pd` route is **Advanced Track only**, requiring Linux, two compatible GPUs
and transfer telemetry. It is not a core Final Lab deliverable. A future
advanced implementation should adapt the Lab 03 router contract rather than
duplicate its source without review.
