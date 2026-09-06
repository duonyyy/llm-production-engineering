# Architecture decision record

This file records decisions that shape the lab suite. A decision is not proof that an experiment succeeded; run evidence remains the source for measured claims.

| ID | Decision | Rationale | Consequence |
|---|---|---|---|
| D001 | Use an evidence-first documentation contract. | Lab results can otherwise blur static inspection, local execution, and reference deployment. | Every result states mode, command/artifact, and limitation. |
| D002 | Treat GTX 3050 Laptop GPU 4 GB as the local baseline. | It is the actual available hardware and cannot safely stand in for multi-GPU topology. | Use small-model/local smoke settings; classify cluster/P-D results as reference-only. |
| D003 | Keep a colocated serving path before distributed paths. | A known working local baseline makes later routing and P/D failures diagnosable. | Local lab progression is serving -> routing/cache contract -> agent boundary -> composed final lab. |
| D004 | Keep prefill/decode disaggregation as a reference topology. | It generally needs a topology and telemetry unavailable on a 4 GB laptop GPU. | The repository can validate configs/contracts locally but must not invent performance data. |
| D005 | Use explicit agent/MCP allowlists and default-deny authorization. | Model text is untrusted and cannot grant authority. | Denial paths are first-class tests and every tool has a bounded schema. |
| D006 | Keep observability identifiers correlated but opaque. | Troubleshooting requires joins across components while evidence must not leak prompts or credentials. | Use task/request/tool IDs; sanitize logs and benchmark artifacts. |

## When to change a decision

Open a new decision entry when a change affects hardware assumptions, trust boundaries, deployment topology, benchmark comparability, or what can be claimed as measured. Link the new entry from the affected lab README and update [PROJECT_STATUS.md](PROJECT_STATUS.md) if the status changes.
