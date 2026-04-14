# finance_saa source-of-truth remediation bundle

This bundle upgrades the finance bootstrap from `memoryd` as a write-through side effect to `memoryd` as the preferred recovery surface.

## What changes

- persist a `session_snapshot` artifact into `memoryd` after each state mutation
- reconstruct local finance session state from the latest snapshot when a session is requested and not already loaded
- keep local in-memory caches as a warm cache, not the only state holder

## Why this matters

The prior step persisted committee artifacts into `memoryd`, but recovery still depended on best-effort artifact recall. Snapshot persistence gives the service a more deterministic bootstrap path without yet requiring a full event-sourced replay engine.

## Replacement files

- `replacements/services/finance_saa/app/main.py`
