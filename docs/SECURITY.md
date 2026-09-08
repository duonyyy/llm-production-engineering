# Security boundary

## 1. Scope

These labs demonstrate production-engineering patterns; they are not a hosted production service. Nevertheless, the configurations, prompts, tools, and benchmark artifacts must be handled as if they could affect a real deployment.

## 2. Assets and trust boundaries

| Asset | Boundary | Required control |
|---|---|---|
| Model/API credentials | local shell, CI secret store, deployment secret | never commit; inject at runtime; rotate if exposed |
| Prompts and tool payloads | user/agent/tool boundary | minimize retention; sanitize evidence; validate schemas |
| MCP/tool authority | agent to external action boundary | allowlist tools and arguments; default deny |
| Model server and router | caller to data-plane boundary | authenticated access in a deployed setup; bounded inputs and timeouts |
| RAG documents, chunks and index | ingestion/retrieval boundary | source provenance, versioned index and access filter before context exposure |
| Kubernetes credentials | operator/control-plane boundary | least-privilege RBAC; separate service accounts per role |
| Logs and benchmark runs | evidence boundary | redact secrets and identifiers; restrict access as needed |

## 3. Non-negotiable rules

- Do not commit `.env` files, tokens, kubeconfigs, private endpoints, or model-download credentials.
- Do not give an agent general shell, filesystem, network, or credential access merely to make a demo work.
- Tool identity and user authorization must be verified at the boundary; a model instruction is not authorization.
- Validate tool input against an explicit schema and enforce resource/time limits.
- Treat model output as untrusted data, especially when it can select tools, URLs, or deployment operations.
- Treat retrieved documents as untrusted input: preserve source identity, enforce access scope before context exposure, and abstain when authorized evidence is absent.
- Separate a user-visible error from internal diagnostics. Error messages must not disclose secrets or infrastructure topology.

## 4. Agent and MCP policy

The secure default is a small capability set:

```text
allowed task -> named tool -> schema-validated arguments -> bounded execution -> audited result
```

Each tool call should record the task ID, tool name, policy decision, and sanitized result status. It should not log secrets or raw sensitive payloads. A denied tool call remains denied; retrying it through a different unreviewed path is a policy failure.

## 5. Deployment policy

For the reference Kubernetes path:

- bind service accounts to the minimal namespace/resource verbs;
- do not mount host paths, Docker sockets, or broad kubeconfigs into model/router/agent workloads;
- set CPU, memory, and GPU limits deliberately;
- isolate secrets from ConfigMaps and from application logs;
- review network exposure before using an ingress or public endpoint.

## 6. Incident handling in a learning repository

If a credential is exposed, revoke or rotate it first, remove it from the working tree/history according to the owner’s policy, then document the remediation without republishing the secret. For vulnerability reporting guidance, see the repository-level [SECURITY.md](../SECURITY.md).
