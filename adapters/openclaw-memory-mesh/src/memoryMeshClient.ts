export type ScopeEnvelope = {
  user_id: string;
  agent_id: string;
  run_id: string;
  workload_id: string;
  workspace_id?: string | null;
  channel?: string | null;
  thread_id?: string | null;
  source_interface: string;
  metadata?: Record<string, unknown>;
};

export type RecallPayload = {
  envelope: ScopeEnvelope;
  query: string;
  top_k?: number;
  scope_order?: string[];
  include_relations?: boolean;
  include_raw_events?: boolean;
  filters?: Record<string, unknown>;
};

export type MemoryHit = {
  memory_id: string;
  text: string;
  score: number;
  source: string;
  scope: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  event_id?: string | null;
};

export type CompiledWorkloadConfig = {
  workload_id: string;
  recall_scope_order?: string[];
  recall_top_k_limit?: number;
  local_first?: boolean;
  writeback_enabled?: boolean;
  allow_backend_persistence?: boolean;
  attachments?: object[];
  peers?: object[];
  export_policies?: object[];
  conflict_policies?: object[];
};

export type RecallResponse = {
  query: string;
  hits: MemoryHit[];
  compiled_policy: CompiledWorkloadConfig | Record<string, unknown> | null;
};

export type WritePayload = {
  envelope: ScopeEnvelope;
  content: string;
  memoryClass: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
};

export type WriteResponse = {
  event_id: string;
  backend_memory_ids?: string[];
  stored_locally?: boolean;
};

export class MemoryMeshClient {
  constructor(private readonly baseUrl: string, private readonly apiKey: string) {}

  private get headers(): HeadersInit {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;
    return headers;
  }

  async getCompiledConfig(workloadId: string): Promise<CompiledWorkloadConfig> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/v1/config/${encodeURIComponent(workloadId)}`, {
      method: "GET",
      headers: this.headers,
    });
    if (!response.ok) {
      throw new Error(`memory config fetch failed: ${response.status} ${response.statusText}`);
    }
    return await response.json() as CompiledWorkloadConfig;
  }

  async recall(payload: RecallPayload): Promise<RecallResponse> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/v1/recall`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        scope_order: ["run", "agent", "user"],
        include_relations: false,
        include_raw_events: false,
        filters: {},
        ...payload,
      }),
    });
    if (!response.ok) {
      throw new Error(`memory recall failed: ${response.status} ${response.statusText}`);
    }
    return await response.json() as RecallResponse;
  }

  async write(payload: WritePayload): Promise<WriteResponse> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/v1/write`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        envelope: payload.envelope,
        content: payload.content,
        memory_class: payload.memoryClass,
        metadata: payload.metadata ?? {},
        tags: payload.tags ?? [],
        persist_to_backend: true,
      }),
    });
    if (!response.ok) {
      throw new Error(`memory write failed: ${response.status} ${response.statusText}`);
    }
    return await response.json() as WriteResponse;
  }
}
