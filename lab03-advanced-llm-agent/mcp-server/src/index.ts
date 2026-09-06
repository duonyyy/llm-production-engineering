import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "lab03-readonly-observer",
  version: "0.1.0",
});

const textResult = (value: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(value) }],
});

server.registerTool(
  "get_cluster_summary",
  {
    title: "Get cluster summary",
    description: "Return a bounded, read-only summary for the lab namespace. No secrets and no pod exec.",
    inputSchema: {
      namespace: z.string().regex(/^[a-z0-9-]{1,63}$/).default("lab03"),
    },
  },
  async ({ namespace }) => textResult({
    source: "lab03-observer-contract",
    namespace,
    status: "not_connected_to_live_cluster",
    allowed_verbs: ["get", "list", "watch"],
  }),
);

server.registerTool(
  "get_model_health",
  {
    title: "Get model health",
    description: "Return bounded health metadata for a named lab component; never executes a command.",
    inputSchema: {
      component: z.enum(["colocated", "prefill", "decode", "router"]).default("router"),
    },
  },
  async ({ component }) => textResult({
    source: "lab03-observer-contract",
    component,
    status: "probe_not_run",
    metrics: { ttft_ms: null, tpot_ms: null, kv_transfer_ms: null },
  }),
);

server.registerTool(
  "get_recent_metrics",
  {
    title: "Get recent metrics",
    description: "Return a bounded read-only metric schema. It does not read arbitrary files or accept PromQL.",
    inputSchema: {
      limit: z.number().int().min(1).max(100).default(20),
    },
  },
  async ({ limit }) => textResult({
    source: "lab03-observer-contract",
    limit,
    status: "no_live_snapshot",
    fields: ["task_id", "llm_request_id", "tool_call_id", "ttft_ms", "tpot_ms", "queue_ms", "kv_usage", "transfer_failures"],
  }),
);

const transport = new StdioServerTransport();
await server.connect(transport);
