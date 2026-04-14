# OpenClaw Edge Memory

This note records the current hybrid memory direction for the OpenClaw adapter in `memory-mesh`.

## Intent

We keep `memoryd` as the canonical mesh API and add a bounded edge-memory layer in the OpenClaw environment.

The edge layer is not the sovereign truth source. It exists for:

- local bootstrap;
- local-first recall when policy allows it;
- environment continuity during degraded network conditions;
- operator-facing projections.

## Current implementation

The current branch now includes:

- adapter configuration for edge-memory enablement and local recall thresholds;
- a file-backed edge-memory mirror with generated `MEMORY.md` projection;
- adapter-side recall merge logic across edge and mesh hits;
- `memoryd` recall ordering that respects compiled `local_first` and `recall_scope_order` more concretely.

## Current scope model

The effective scope ordering now recognizes these scopes:

1. `thread`
2. `channel`
3. `workspace`
4. `run`
5. `agent`
6. `user`

This ordering is used to make local environment recall more specific before falling back to broader durable context.

## What remains

This is still phase one. The remaining work is:

- replace the JSON-backed edge store with SQLite and explicit sync state;
- add background sync and conflict handling;
- promote edge-memory behavior from tool-only paths toward lifecycle hooks;
- refine projection and promotion rules by memory class.
