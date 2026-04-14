import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

import type { MemoryHit, ScopeEnvelope } from "./memoryMeshClient.ts";

export type EdgeMemoryEntry = {
  local_id: string;
  mesh_event_id?: string | null;
  content: string;
  memory_class: string;
  envelope: ScopeEnvelope;
  metadata: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
  sync_state: "local_only" | "pending_write" | "synced" | "conflict";
};

type EdgeMemoryStoreOptions = {
  enabled: boolean;
  baseDir: string;
};

const DEFAULT_SCOPE_ORDER = ["thread", "channel", "workspace", "run", "agent", "user"];

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .split(/\s+/)
      .map((token) => token.trim().replace(/^[^\w]+|[^\w]+$/g, "").toLowerCase())
      .filter((token) => token.length > 0),
  );
}

function scopeNameForEnvelope(request: ScopeEnvelope, candidate: ScopeEnvelope): string {
  if (candidate.user_id != request.user_id) {
    return "none";
  }
  if (request.thread_id && candidate.thread_id === request.thread_id) {
    return "thread";
  }
  if (request.channel && candidate.channel === request.channel) {
    return "channel";
  }
  if (request.workspace_id && candidate.workspace_id === request.workspace_id) {
    return "workspace";
  }
  if (candidate.run_id === request.run_id) {
    return "run";
  }
  if (candidate.agent_id === request.agent_id) {
    return "agent";
  }
  return "user";
}

function buildScopeOrder(scopeOrder?: string[]): string[] {
  const merged = [...DEFAULT_SCOPE_ORDER];
  for (const item of scopeOrder ?? []) {
    if (item && !merged.includes(item)) {
      merged.push(item);
    }
  }
  return merged;
}

function scopeRank(scopeName: string, scopeOrder: string[]): number {
  const idx = scopeOrder.indexOf(scopeName);
  if (idx < 0) {
    return 0;
  }
  return scopeOrder.length - idx;
}

function overlapScore(query: string, text: string): number {
  const queryTokens = tokenize(query);
  const textTokens = tokenize(text);
  let overlap = 0;
  for (const token of queryTokens) {
    if (textTokens.has(token)) {
      overlap += 1;
    }
  }
  if (overlap === 0 && text.toLowerCase().includes(query.toLowerCase())) {
    return 1;
  }
  return overlap;
}

export class EdgeMemoryStore {
  private readonly entriesPath: string;
  private readonly projectionPath: string;

  constructor(private readonly options: EdgeMemoryStoreOptions) {
    const baseDir = path.isAbsolute(options.baseDir) ? options.baseDir : path.join(os.homedir(), options.baseDir);
    this.entriesPath = path.join(baseDir, "edge-memory.json");
    this.projectionPath = path.join(baseDir, "MEMORY.md");
  }

  get enabled(): boolean {
    return this.options.enabled;
  }

  get baseDir(): string {
    return path.dirname(this.entriesPath);
  }

  private async ensureReady(): Promise<void> {
    if (!this.enabled) {
      return;
    }
    await fs.mkdir(this.baseDir, { recursive: true });
    try {
      await fs.access(this.entriesPath);
    } catch {
      await fs.writeFile(this.entriesPath, "[]\n", "utf-8");
    }
  }

  private async readEntries(): Promise<EdgeMemoryEntry[]> {
    if (!this.enabled) {
      return [];
    }
    await this.ensureReady();
    try {
      const raw = await fs.readFile(this.entriesPath, "utf-8");
      const parsed = JSON.parse(raw) as EdgeMemoryEntry[];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  private async writeEntries(entries: EdgeMemoryEntry[]): Promise<void> {
    if (!this.enabled) {
      return;
    }
    await this.ensureReady();
    await fs.writeFile(this.entriesPath, `${JSON.stringify(entries, null, 2)}\n`, "utf-8");
    await this.writeProjection(entries);
  }

  private async writeProjection(entries: EdgeMemoryEntry[]): Promise<void> {
    const lines = [
      "# OpenClaw Edge Memory",
      "",
      "This file is a generated projection of the environment-local edge memory mirror.",
      "",
    ];
    for (const entry of entries.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at))) {
      lines.push(`## ${entry.memory_class}`);
      lines.push(`- content: ${entry.content}`);
      lines.push(`- sync_state: ${entry.sync_state}`);
      lines.push(`- mesh_event_id: ${entry.mesh_event_id ?? "none"}`);
      lines.push(`- updated_at: ${entry.updated_at}`);
      lines.push("");
    }
    await fs.writeFile(this.projectionPath, `${lines.join("\n")}\n`, "utf-8");
  }

  async search(query: string, envelope: ScopeEnvelope, topK: number, scopeOrder?: string[]): Promise<MemoryHit[]> {
    if (!this.enabled) {
      return [];
    }
    const entries = await this.readEntries();
    const orderedScopes = buildScopeOrder(scopeOrder);
    const hits: MemoryHit[] = [];
    for (const entry of entries) {
      const scope = scopeNameForEnvelope(envelope, entry.envelope);
      if (scope === "none") {
        continue;
      }
      const overlap = overlapScore(query, entry.content);
      if (overlap <= 0) {
        continue;
      }
      hits.push({
        memory_id: entry.local_id,
        text: entry.content,
        score: overlap + scopeRank(scope, orderedScopes),
        source: "edge.local",
        scope,
        tags: entry.tags,
        metadata: {
          ...entry.metadata,
          sync_state: entry.sync_state,
          mesh_event_id: entry.mesh_event_id ?? null,
        },
        event_id: entry.mesh_event_id ?? null,
      });
    }
    hits.sort((left, right) => right.score - left.score);
    return hits.slice(0, topK);
  }

  async mirrorWrite(args: {
    envelope: ScopeEnvelope;
    content: string;
    memoryClass: string;
    metadata?: Record<string, unknown>;
    tags?: string[];
    meshEventId?: string | null;
  }): Promise<EdgeMemoryEntry | null> {
    if (!this.enabled) {
      return null;
    }
    const entries = await this.readEntries();
    const timestamp = new Date().toISOString();
    const localId = args.meshEventId ?? `edge-${Date.now().toString(36)}`;
    const entry: EdgeMemoryEntry = {
      local_id: localId,
      mesh_event_id: args.meshEventId ?? null,
      content: args.content,
      memory_class: args.memoryClass,
      envelope: args.envelope,
      metadata: args.metadata ?? {},
      tags: args.tags ?? [],
      created_at: timestamp,
      updated_at: timestamp,
      sync_state: args.meshEventId ? "synced" : "pending_write",
    };
    const idx = entries.findIndex((item) => item.local_id === localId || (args.meshEventId && item.mesh_event_id === args.meshEventId));
    if (idx >= 0) {
      entries[idx] = { ...entries[idx], ...entry, created_at: entries[idx].created_at };
    } else {
      entries.push(entry);
    }
    await this.writeEntries(entries);
    return entry;
  }
}
