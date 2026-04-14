import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import { resolvePluginConfig } from "./src/config.ts";
import { EdgeMemoryStore } from "./src/edgeMemoryStore.ts";
import {
  MemoryMeshClient,
  type CompiledWorkloadConfig,
  type MemoryHit,
  type RecallResponse,
  type ScopeEnvelope,
  type WriteResponse,
} from "./src/memoryMeshClient.ts";

const DEFAULT_SCOPE_ORDER = ["thread", "channel", "workspace", "run", "agent", "user"];

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

function buildScopeOrder(scopeOrder?: string[]): string[] {
  const ordered = [...DEFAULT_SCOPE_ORDER];
  for (const item of scopeOrder ?? []) {
    if (item && !ordered.includes(item)) {
      ordered.push(item);
    }
  }
  return ordered;
}

function scopeRank(scopeName: string, scopeOrder: string[]): number {
  const idx = scopeOrder.indexOf(scopeName);
  if (idx < 0) {
    return 0;
  }
  return scopeOrder.length - idx;
}

function sourceRank(source: string, localFirst: boolean): number {
  if (!localFirst) {
    return 0;
  }
  return source.startsWith("edge.") || source.startsWith("memoryd.") ? 1 : 0;
}

function hitSortKey(hit: MemoryHit, scopeOrder: string[], localFirst: boolean): [number, number, number] {
  return [sourceRank(hit.source, localFirst), scopeRank(hit.scope, scopeOrder), Number(hit.score ?? 0)];
}

function compareHits(left: MemoryHit, right: MemoryHit, scopeOrder: string[], localFirst: boolean): number {
  const leftKey = hitSortKey(left, scopeOrder, localFirst);
  const rightKey = hitSortKey(right, scopeOrder, localFirst);
  for (let index = 0; index < leftKey.length; index += 1) {
    if (leftKey[index] !== rightKey[index]) {
      return rightKey[index] - leftKey[index];
    }
  }
  return right.text.length - left.text.length;
}

function mergeHits(edgeHits: MemoryHit[], meshHits: MemoryHit[], scopeOrder: string[], localFirst: boolean, limit: number): MemoryHit[] {
  const retained = new Map<string, MemoryHit>();
  const consider = (hit: MemoryHit) => {
    const key = hit.event_id ?? hit.memory_id ?? `${hit.source}:${hit.text}`;
    const existing = retained.get(key);
    if (!existing || compareHits(hit, existing, scopeOrder, localFirst) < 0) {
      retained.set(key, hit);
    }
  };
  for (const hit of [...edgeHits, ...meshHits]) {
    consider(hit);
  }
  return Array.from(retained.values())
    .sort((left, right) => compareHits(left, right, scopeOrder, localFirst))
    .slice(0, limit);
}

export default definePluginEntry({
  id: "memory-mesh",
  name: "Memory Mesh",
  description: "Memory search and write tools backed by memoryd",
  register(api) {
    const pluginConfig = resolvePluginConfig(api.pluginConfig);
    const client = new MemoryMeshClient(pluginConfig.baseUrl, pluginConfig.apiKey);
    const edgeStore = new EdgeMemoryStore({
      enabled: pluginConfig.edgeMemoryEnabled,
      baseDir: pluginConfig.edgeMemoryDir,
    });

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
        const requestedTopK = typeof (params as any).top_k === "number" ? (params as any).top_k : 5;
        let compiledPolicy: CompiledWorkloadConfig | null = null;
        try {
          compiledPolicy = await client.getCompiledConfig(envelope.workload_id);
        } catch {
          compiledPolicy = null;
        }

        const scopeOrder = buildScopeOrder(compiledPolicy?.recall_scope_order);
        const limit = Math.min(requestedTopK, compiledPolicy?.recall_top_k_limit ?? requestedTopK);
        const localFirst = compiledPolicy?.local_first ?? true;
        const edgeHits = await edgeStore.search(String((params as any).query), envelope, limit, scopeOrder);

        let meshResponse: RecallResponse = {
          query: String((params as any).query),
          hits: [],
          compiled_policy: compiledPolicy,
        };
        const shouldQueryMesh = !pluginConfig.edgeMemoryEnabled || !localFirst || edgeHits.length < pluginConfig.localRecallMinHits;
        if (shouldQueryMesh) {
          meshResponse = await client.recall({
            envelope,
            query: String((params as any).query),
            top_k: limit,
            scope_order: scopeOrder,
          });
        }

        const mergedHits = mergeHits(edgeHits, Array.isArray(meshResponse.hits) ? meshResponse.hits : [], scopeOrder, localFirst, limit);
        const result = {
          query: String((params as any).query),
          hits: mergedHits,
          compiled_policy: meshResponse.compiled_policy ?? compiledPolicy,
          edge: {
            enabled: pluginConfig.edgeMemoryEnabled,
            path: edgeStore.baseDir,
            local_first: localFirst,
            local_hit_count: edgeHits.length,
            mesh_requested: shouldQueryMesh,
            local_recall_min_hits: pluginConfig.localRecallMinHits,
          },
        };
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
        const memoryClass = safeString((params as any).memory_class, pluginConfig.writebackClass);
        const result = await client.write({
          envelope,
          content: String((params as any).content),
          memoryClass,
          metadata: ((params as any).metadata ?? {}) as Record<string, unknown>,
          tags: Array.isArray((params as any).tags) ? ((params as any).tags as string[]) : [],
        });
        const writeResponse = result as WriteResponse;
        const mirrored = await edgeStore.mirrorWrite({
          envelope,
          content: String((params as any).content),
          memoryClass,
          metadata: ((params as any).metadata ?? {}) as Record<string, unknown>,
          tags: Array.isArray((params as any).tags) ? ((params as any).tags as string[]) : [],
          meshEventId: writeResponse.event_id,
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  ...writeResponse,
                  edge: {
                    mirrored: mirrored !== null,
                    path: edgeStore.baseDir,
                  },
                },
                null,
                2,
              ),
            },
          ],
        };
      },
    });
  },
});
