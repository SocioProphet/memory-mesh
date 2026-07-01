from __future__ import annotations

import unittest

from services.workspace_ingestion.app import main as svc
from services.workspace_ingestion.app.mapping import build_graph
from services.workspace_ingestion.app.models import (
    CSKGEdge,
    GraphBundle,
    IngestWorkspaceRequest,
    RetractRequest,
)

CONTACT_MOM = {
    "contactId": "c-mom", "contactClass": "person", "displayName": "Mom",
    "labels": ["family"], "sourceId": "workspace-source:contacts/mom",
    "socialProfiles": [{"platform": "linkedin", "handle": "ada"}],
}
CONTACT_JAMIE = {
    "contactId": "c-jamie", "contactClass": "person", "displayName": "Jamie",
    "organizationRef": "Acme Music", "labels": ["bandmate"],
    "sourceId": "workspace-source:contacts/jamie",
}
EVENT_PRACTICE = {
    "eventId": "e-practice", "title": "Band practice",
    "sourceId": "workspace-source:calendar/practice",
    "attendees": [
        {"isSelf": True, "email": "me@x.com"},
        {"contactRef": "c-jamie", "name": "Jamie"},
    ],
}
MAIL_JAMIE = {
    "messageId": "m-1", "threadId": "t-1",
    "from": {"email": "jamie@x.com", "name": "Jamie", "contactRef": "c-jamie"},
    "sourceId": "workspace-source:mail/jamie-thread",
}
ARTIFACT_SETLIST = {
    "artifactId": "a-setlist", "title": "Setlist",
    "sourceId": "workspace-source:office/setlist",
}

SELF = "cskg-node://self/lord"


class MappingTests(unittest.TestCase):
    def test_single_self_anchor_and_family_vs_social(self):
        b = build_graph(SELF, "lord", contacts=[CONTACT_MOM, CONTACT_JAMIE])
        selves = [n for n in b.nodes if n.node_type == "Self"]
        self.assertEqual(len(selves), 1)
        rels = {(e.node1, e.node2): e.relation for e in b.edges}
        mom = "cskg-node://person/c_mom"
        jamie = "cskg-node://person/c_jamie"
        self.assertEqual(rels[(SELF, mom)], "relatedTo")   # family hint
        self.assertEqual(rels[(SELF, jamie)], "knows")     # social
        # worksAt to org
        self.assertEqual(rels[(jamie, "cskg-node://organization/acme_music")], "worksAt")

    def test_every_element_is_provenance_bound_to_workspace_source(self):
        b = build_graph(SELF, "lord", contacts=[CONTACT_JAMIE], events=[EVENT_PRACTICE], artifacts=[ARTIFACT_SETLIST])
        for n in b.nodes:
            self.assertTrue(n.provenance_refs, f"node {n.node_id} has no provenance")
        for e in b.edges:
            self.assertTrue(all(r.startswith("workspace-source:") or r == "workspace-source:onboarding" for r in e.provenance_refs) or e.provenance_refs)

    def test_mail_resolves_onto_same_person_no_dup(self):
        b = build_graph(SELF, "lord", contacts=[CONTACT_JAMIE], messages=[MAIL_JAMIE])
        jamies = [n for n in b.nodes if n.label == "Jamie"]
        self.assertEqual(len(jamies), 1)  # mail reused the contact node
        rels = {e.relation for e in b.edges if e.node2 == "cskg-node://person/c_jamie"}
        self.assertIn("communicatedWith", rels)
        self.assertIn("knows", rels)

    def test_social_profile_becomes_reference_only_projection(self):
        b = build_graph(SELF, "lord", contacts=[CONTACT_MOM])
        mom = next(n for n in b.nodes if n.label == "Mom")
        self.assertTrue(mom.external_projection_refs)
        self.assertTrue(mom.external_projection_refs[0].startswith("projection:social/"))


class _FakeHellGraph:
    """Records calls; simulates HellGraph being present."""
    enabled = True

    def __init__(self):
        self.ingested: GraphBundle | None = None
        self.retracted: list[str] | None = None

    async def normalize(self, edges):
        return edges

    async def ingest(self, bundle):
        self.ingested = bundle
        return {"persisted": True, "nodes": len(bundle.nodes), "edges": len(bundle.edges)}

    async def retract(self, source_refs):
        self.retracted = source_refs
        return {"retracted": True, "superseded": len(source_refs)}


class _FakeMemoryd:
    enabled = True

    async def write_summary(self, **kwargs):
        return {"stored": True, "memory_id": "mem-123"}


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._hg, self._md = svc.hellgraph, svc.memoryd
        svc.hellgraph = _FakeHellGraph()
        svc.memoryd = _FakeMemoryd()

    def tearDown(self):
        svc.hellgraph, svc.memoryd = self._hg, self._md

    async def test_ingest_persists_and_writes_back(self):
        req = IngestWorkspaceRequest(
            envelope={"user_id": "lord"},
            contacts=[CONTACT_JAMIE], events=[EVENT_PRACTICE],
            messages=[MAIL_JAMIE], artifacts=[ARTIFACT_SETLIST],
        )
        resp = await svc.ingest_workspace(req, x_api_key=None)
        self.assertEqual(resp.self_ref, "cskg-node://self/lord")
        self.assertTrue(resp.hellgraph["persisted"])
        self.assertEqual(resp.recall_candidate_ref, "mem-123")
        types = sorted({n.node_type for n in resp.bundle.nodes})
        self.assertEqual(types, ["Document", "Event", "Organization", "Person", "Self"])
        self.assertIsNotNone(svc.hellgraph.ingested)

    async def test_dry_run_does_not_persist(self):
        req = IngestWorkspaceRequest(envelope={"user_id": "lord"}, contacts=[CONTACT_MOM], persist=False)
        resp = await svc.ingest_workspace(req, x_api_key=None)
        self.assertEqual(resp.hellgraph, {})
        self.assertIsNone(svc.hellgraph.ingested)

    async def test_retract_supersedes_by_source(self):
        req = RetractRequest(source_refs=["workspace-source:contacts/jamie"])
        resp = await svc.retract(req, x_api_key=None)
        self.assertTrue(resp.hellgraph["retracted"])
        self.assertEqual(svc.hellgraph.retracted, ["workspace-source:contacts/jamie"])


if __name__ == "__main__":
    unittest.main()
