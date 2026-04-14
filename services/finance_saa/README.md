# finance_saa runtime skeleton

This directory contains the first bootstrap runtime slice for the draft `finance.saa.v1` committee contract.

## Scope

This is intentionally a narrow in-memory bootstrap service. It is **not** yet a full committee engine and it is **not** yet a TriTRPC-native runtime. The immediate purpose is to establish a concrete executable surface that mirrors the first committee methods while the memory mesh contract and runtime alignment settle.

## Included bootstrap methods

- `Session.Start`
- `Assumptions.Submit`
- `Proposal.Submit`
- `Proposal.Critique`
- `Risk.Check`
- `Vote.Record`
- `Decision.Select`

## Design constraints

- Reuses the `ScopeEnvelope` shape from `memoryd` semantics.
- Uses explicit `valuation_date` and `data_cutoff` in session context.
- Keeps deterministic math and optimizer integration out of scope for this bootstrap slice.
- Holds state in memory only for now.

## Bootstrap run

```bash
uvicorn services.finance_saa.app.main:app --reload --port 8790
```
