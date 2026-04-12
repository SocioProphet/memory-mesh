# memoryd runtime remediation bundle

This directory captures the exact runtime-alignment patch that should be applied to the existing `services/memoryd/app/*` files to bring `memoryd` closer to the draft `memory.mesh.v1` contract.

## Why this exists

The GitHub connector available in this session can create new files, but it cannot update existing files in-place because the exposed contents write surface does not accept the file `sha` required by GitHub for update operations.

To avoid losing the patch work, this bundle stores full replacement files for the targeted runtime modules.

## Targeted outcomes

- add `event_version`, `config_hash`, and `memory_id` support to runtime models
- enforce `local_first` execution order in recall
- resolve effective scope order from request override, then compiled policy, then default
- hard-filter lexical and vector recall by `workload_id`, and by `workspace_id` when present
- make raw event / relation access policy-gated
- emit more specific memory event types (`memory.recall.*`, `memory.write.*`, `memory.resource.applied`, `memory.config.compiled`)

## Replacement files

- `replacements/services/memoryd/app/models.py`
- `replacements/services/memoryd/app/store.py`
- `replacements/services/memoryd/app/main.py`
- `replacements/services/memoryd/app/sqlite_store.py`
- `replacements/services/memoryd/app/postgres_store.py`
- `replacements/services/memoryd/app/qdrant_index.py`

## Apply strategy

When a write path with existing-file update support is available, these replacements should be copied over the live runtime files, then validated with the existing repo targets:

```bash
python -m py_compile services/memoryd/app/*.py adapters/litellm/*.py scripts/*.py && python -m unittest discover -s services/memoryd/tests -p 'test_*.py'
```

## Important note

This bundle is intentionally conservative. It aims to align the runtime with the new draft contract without broadening scope into a larger redesign.
