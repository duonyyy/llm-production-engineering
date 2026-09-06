# Agent Runtime

This is a small educational runtime, not an autonomous production agent.

Flow:

```text
task -> load durable state -> one deterministic planner/LLM decision
     -> allowlisted read-only MCP tool -> observation -> append event
     -> persist execution state -> answer
```

`session_store.py` uses SQLite for session state, execution checkpoints, audit
events and idempotency keys. The runtime never treats the context window as
durable state. It also fails closed when MCP is absent, the tool is not on the
allowlist, the tool times out, or the MCP server returns an error.

## Run

From a Linux/macOS shell or PowerShell with Python:

```text
python agent/agent_runtime.py --task "check model health" --mock-mcp
```

For a real local MCP process after building `mcp-server`:

```text
python agent/agent_runtime.py --task "check model health" --mcp-command node mcp-server/dist/index.js
```

The mock path is explicitly labelled `MOCK_DEMO`; it is not an inference or
cluster measurement. No write tool is exposed. Any future write action needs a
separate policy boundary, idempotency key and human approval.
