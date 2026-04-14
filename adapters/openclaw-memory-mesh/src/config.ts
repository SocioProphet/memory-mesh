export type PluginConfig = {
  baseUrl: string;
  apiKey: string;
  workloadId: string;
  defaultAgentId: string;
  writebackClass: string;
  edgeMemoryEnabled: boolean;
  edgeMemoryDir: string;
  localRecallMinHits: number;
};

function safeNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function safeBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string" && value.length > 0) {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normalized)) {
      return true;
    }
    if (["0", "false", "no", "off"].includes(normalized)) {
      return false;
    }
  }
  return fallback;
}

export function resolvePluginConfig(input: Record<string, unknown> | undefined): PluginConfig {
  const data = input ?? {};
  const env = typeof process !== "undefined" ? process.env : {};
  const get = (key: string, fallback: string): string => {
    const value = data[key] ?? env?.[key];
    return typeof value === "string" && value.length > 0 ? value : fallback;
  };
  const getNumber = (key: string, fallback: number): number => safeNumber(data[key] ?? env?.[key], fallback);
  const getBoolean = (key: string, fallback: boolean): boolean => safeBoolean(data[key] ?? env?.[key], fallback);
  return {
    baseUrl: get("MEMORYD_BASE_URL", "http://127.0.0.1:8787"),
    apiKey: get("MEMORYD_API_KEY", ""),
    workloadId: get("MEMORYD_WORKLOAD_ID", "openclaw-gateway"),
    defaultAgentId: get("MEMORYD_AGENT_ID", "openclaw-gateway"),
    writebackClass: get("MEMORYD_WRITEBACK_CLASS", "interaction"),
    edgeMemoryEnabled: getBoolean("OPENCLAW_EDGE_MEMORY_ENABLED", true),
    edgeMemoryDir: get("OPENCLAW_EDGE_MEMORY_DIR", ".openclaw/memory-mesh"),
    localRecallMinHits: getNumber("OPENCLAW_LOCAL_RECALL_MIN_HITS", 2),
  };
}
