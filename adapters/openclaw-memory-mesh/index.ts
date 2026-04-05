import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import { resolvePluginConfig } from "./src/config.ts";
import { MemoryMeshClient, type ScopeEnvelope } from "./src/memoryMeshClient.ts";

function safeString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function buildEnvelope(pluginConfig: ReturnType<typeof resolvePluginConfig>, api: any, params?: Record<string, unknown>): ScopeEnvelope {
  const metadata = (params?.metadata ?? {}) as Record<string, unknown>;
  const userId = safeString(params?.user_id ?? metadata.user_id, "unknown-user");
  const runId = safeString(params?.run_id ?? metadata.run_id, `openclaw:${userId}`);
  return {
    user_id: userId,
    agent_id: safeString(params?.agent_id ?? metadata.agent_id, pluginConfig.defaultAgentId),
    run_id: runId,
    workload_id: safeString(params?.workload_id ?? metadata.workload_id, pluginConfig.workloadId),
    workspace_id: typeof metadata.workspace_id === "string" ? metadata.workspace_id : null,
    channel: typeof metadata.channel === "string" ? metadata.channel : "openclaw",
    thread_id: typeof metadata.thread_id === "string" ? metadata.thread_id : null,
    source_interface: "openclaw",
    metadata,
  };
}

export default definePluginEntry({
  id: "memory-mesh",
  name: "Memory Mesh",
  description: "Memory search and write tools backed by memoryd",
  register(api) {
    const pluginConfig = resolvePluginConfig(api.pluginConfig);
    const client = new MemoryMeshClient(pluginConfig.baseUrl, pluginConfig.apiKey);

    api.registerTool({
      name: "memory_search",
      description: "Search the shared memory mesh for relevant context.",
      parameters: Type.Object({
        query: Type.String({ minLength: 1 }),
        user_id: Type.Optional(Type.String()),
        agent_id: Type.Optional(Type.String()),
        run_id: Type.Optional(Type.String()),
        workload_id: Type.Optional(Type.String()),
        top_k: Type.Optional(Type.Number({ minimum: 1, maximum: 20 })),
        metadata: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(_toolCallId, params) {
        const envelope = buildEnvelope(pluginConfig, api, params as Record<string, unknown>);
        const result = await client.recall({
          envelope,
          query: String((params as any).query),
          top_k: typeof (params as any).top_k === "number" ? (params as any).top_k : 5,
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      },
    });

    api.registerTool({
      name: "memory_write",
      description: "Write a distilled fact, preference, decision, or interaction into the memory mesh.",
      parameters: Type.Object({
        content: Type.String({ minLength: 1 }),
        memory_class: Type.Optional(Type.String()),
        user_id: Type.Optional(Type.String()),
        agent_id: Type.Optional(Type.String()),
        run_id: Type.Optional(Type.String()),
        workload_id: Type.Optional(Type.String()),
        metadata: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
        tags: Type.Optional(Type.Array(Type.String())),
      }),
      async execute(_toolCallId, params) {
        const envelope = buildEnvelope(pluginConfig, api, params as Record<string, unknown>);
        const result = await client.write({
          envelope,
          content: String((params as any).content),
          memoryClass: safeString((params as any).memory_class, pluginConfig.writebackClass),
          metadata: ((params as any).metadata ?? {}) as Record<string, unknown>,
          tags: Array.isArray((params as any).tags) ? ((params as any).tags as string[]) : [],
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      },
    });
  },
});
