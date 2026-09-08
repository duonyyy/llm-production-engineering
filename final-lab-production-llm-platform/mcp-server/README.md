# MCP server boundary

This boundary exposes a minimal read-only operational surface. It must enforce
application authorization independently from MCP protocol initialization and
must validate every argument against the tool manifest.

Tool implementation is intentionally deferred. Any future tool must be added
to `tool_manifest.yaml`, tested for a denial path, and reviewed against
`../contracts/error_policy.md` before being exposed to the agent.
