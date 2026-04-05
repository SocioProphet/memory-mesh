export type PluginConfig = {
  baseUrl: string;
  apiKey: string;
  workloadId: string;
  defaultAgentId: string;
  writebackClass: string;
};

export function resolvePluginConfig(input: Record<string, unknown> | undefined): PluginConfig {
  const data = input ?? {};
  const env = typeof process !== 'undefined' ? process.env : {};
  const get = (key: string, fallback: string): string => {
    const value = data[key] ?? env?.[key];
    return typeof value === 'string' && value.length > 0 ? value : fallback;
  };
  return {
    baseUrl: get('MEMORYD_BASE_URL', 'http://127.0.0.1:8787'),
    apiKey: get('MEMORYD_API_KEY', ''),
    workloadId: get('MEMORYD_WORKLOAD_ID', 'openclaw-gateway'),
    defaultAgentId: get('MEMORYD_AGENT_ID', 'openclaw-gateway'),
    writebackClass: get('MEMORYD_WRITEBACK_CLASS', 'interaction'),
  };
}
