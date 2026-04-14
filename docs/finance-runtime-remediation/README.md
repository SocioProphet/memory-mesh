# finance_saa memory integration remediation bundle

This directory captures the next bootstrap patch for wiring `services/finance_saa/` into the aligned `memoryd` substrate.

## Goals

- persist finance committee artifacts into `memoryd` using the existing `/v1/write` surface
- keep the bootstrap service executable while adding governed artifact writeback
- prepare for later replacement of ephemeral in-memory state with recovered memory-backed state

## Replacement files

- `replacements/services/finance_saa/requirements.txt`
- `replacements/services/finance_saa/app/models.py`
- `replacements/services/finance_saa/app/memory_mesh_client.py`
- `replacements/services/finance_saa/app/main.py`

## Notes

This is still a bootstrap step. It adds memory-backed persistence and basic recall hooks but does not yet make the service fully TriTRPC-native or fully reconstruct state from the memory substrate.
