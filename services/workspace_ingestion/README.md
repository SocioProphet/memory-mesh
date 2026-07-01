# workspace_ingestion — Personal Knowledge Graph runtime

Turns prophet-workspace canonical objects into the person-graph on the managed
HellGraph. This is the **runtime** half of the PKG program (the contract lives in
prophet-workspace as `PersonalContextGraph`; the substrate is the managed
HellGraph service in prophet-platform).

## Flow

```
WorkspaceSource records            mapping.py            HellGraph (managed)
(contacts/calendar/mail/office) ─▶ build_graph() ─▶ /cskg/normalize ─▶ /v1/ingest
                                        │                                    │
                                   CSKG nodes/edges              memoryd /v1/write
                                   provenance-bound              (writeback summary)
```

- **`mapping.py`** — pure `WorkspaceSource → CSKGNode/CSKGEdge`. Family vs. social
  relation from contact labels; `worksAt` from `organizationRef`; `participatedIn`
  from event attendees; `communicatedWith` from mail; `authored` from artifacts.
  Every element carries `provenance_refs` = the originating `workspace-source:` id.
- **`hellgraph_client.py`** — `/cskg/normalize` (refine relations) → `/v1/ingest`
  (persist as GraphNode/GraphEdge; workspace imports = `confirmed_relation`) →
  `/v1/retract` (retention). Graceful-degrade when `HELLGRAPH_URL` is unset.
- **`main.py`** — `POST /v1/ingest/workspace`, `POST /v1/retract`, `GET /healthz`.

## Config

| Env | Purpose |
|---|---|
| `HELLGRAPH_URL` | managed HellGraph base URL (e.g. `http://hellgraph:8850`); unset ⇒ dry-run |
| `MEMORYD_BASE_URL` | memoryd for writeback summary; unset ⇒ skipped |
| `WORKSPACE_INGESTION_REQUIRE_API_KEY` / `_API_KEY` | optional API-key gate |

## Test

```
python -m unittest discover -s services/workspace_ingestion/tests -p 'test_*.py'
```

Runs without a live HellGraph/memoryd (clients graceful-degrade; service tests use fakes).
