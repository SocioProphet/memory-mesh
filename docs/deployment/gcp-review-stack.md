# Google Cloud review stack

## Goal

Stand up a shared review environment that preserves the real stateful/stateless shape of the system while staying simple enough for early review and testing.

## Recommended first review stack

- GKE Autopilot cluster
- Artifact Registry for images
- Cloud SQL for PostgreSQL
- Qdrant as a StatefulSet on GKE
- `memoryd` as a Deployment on GKE
- optional LiteLLM and OpenClaw as Deployments on GKE
- Secret Manager for credentials and configuration values

## Why this is the recommended first cloud model

This model gives us:

- a real cluster for service topology and internal networking;
- a durable SQL backend without forcing us to self-host every stateful dependency immediately;
- a stateful home for Qdrant that matches its operational shape;
- a clean path from local `arm64` development to cloud `amd64` or mixed-arch deployments.

## Why not Cloud Run as the primary topology

Cloud Run is appropriate for stateless services and sidecars, but the full system has a stateful vector engine and benefits from cluster semantics. Cloud Run remains a valid secondary option for stateless-only review services.

## Review topology

- `memoryd` connects to Cloud SQL over private connectivity and to Qdrant via an internal Kubernetes service.
- Qdrant stores its data on a persistent volume.
- Optional LiteLLM or OpenClaw pods call `memoryd` through a cluster-internal service.
- Images come from Artifact Registry and should be deployed by digest.

## Deployment order

1. Create Artifact Registry repositories.
2. Build and push images.
3. Create the GKE Autopilot cluster.
4. Create the Cloud SQL PostgreSQL instance.
5. Apply the Kubernetes manifests for namespace, secrets, Qdrant, and `memoryd`.
6. Verify internal connectivity.
7. Add LiteLLM and OpenClaw once the core stack is healthy.

## Architecture choices

### Canonical store

The review stack uses Cloud SQL for PostgreSQL. This reduces operational drag while still keeping the application plane self-managed.

### Vector store

The review stack uses self-managed Qdrant on GKE because the vector path is part of the application substrate we want to evaluate, not just a disposable dependency.

### Image strategy

Build multi-arch images. Even if the first review cluster is `amd64`, multi-arch images keep the Mac M2 local path and the cluster path aligned.

## Acceptance checks

- `memoryd` health endpoint is green.
- `memoryd` can append an event and store a local memory.
- a recall request returns the written item.
- Qdrant persistent volume survives a pod restart.
- the deployed image reference is digest-based.

## Alternative review model

If we want the lightest-weight public review path:

- run `memoryd` on Cloud Run;
- keep PostgreSQL in Cloud SQL;
- keep Qdrant on GKE or a VM;
- accept that this is a split topology for review only.

Use this only when the objective is a quick stateless review surface, not topology fidelity.
