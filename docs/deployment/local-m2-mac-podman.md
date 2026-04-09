# Local deployment on an M2 Mac with Podman

## Goal

Run a realistic local `memorymesh` stack on an Apple Silicon Mac using Podman as the container runtime, with PostgreSQL and Qdrant in containers and `memoryd` as the application edge.

## Recommended local shape

The default local stack is:

- `memoryd`
- PostgreSQL
- Qdrant

Optional host-local processes:

- GPT4All, LM Studio, or Ollama
- OpenClaw running from source for fast iteration
- Stagehand/browser debugging tools

## Why Podman here

Podman on macOS runs through a Linux virtual machine. That is useful for us because it keeps the developer environment container-native while still being laptop-local.

We also want Apple Silicon to be a first-class build target. That means `arm64` images should be the default local path.

## Prerequisites

- Podman Desktop or Podman installed on macOS
- a running Podman machine
- a Compose provider available to `podman compose`
- Python locally only if you want to run repo scripts outside containers

## Environment

Copy the example environment file.

```bash
cp deploy/local/.env.example deploy/local/.env
```

Set at least:

- `MEMORYD_API_KEY`
- `MEMORYMESH_STORE_URI`
- optional Qdrant and Mem0 settings

## Recommended local sequence

### 0. Operator shortcuts

The repository now includes a root `Makefile` with the main local operator paths:

```bash
make local-preflight
make local-up
make local-status
make local-smoke
make local-debug
make local-down
make local-reset
```

These commands wrap the scripts below.

### 1. Preflight the workstation

```bash
make local-preflight
# or: bash deploy/local/scripts/preflight-podman-m2.sh
```

This checks:

- Podman installation
- compose-provider availability
- required repo files
- expected local ports
- basic Apple Silicon assumptions

### 2. Bootstrap the stack

```bash
make local-up
# or: bash deploy/local/scripts/bootstrap-podman-m2.sh
```

This script:

- runs the preflight helper;
- initializes a Podman machine if needed;
- starts the machine;
- verifies the socket is available;
- launches the compose stack.

### 3. Inspect current status

```bash
make local-status
# or: bash deploy/local/scripts/status-local.sh
```

This shows compose status and checks the `memoryd` and Qdrant health endpoints.

### 4. Run the smoke test

```bash
make local-smoke
# or: bash deploy/local/scripts/smoke-local.sh
```

The smoke test writes a memory and then recalls it.

### 5. Collect a debug bundle if bring-up fails

```bash
make local-debug
# or: bash deploy/local/scripts/collect-local-debug.sh
```

This writes a timestamped local debug bundle under `.artifacts/local-debug/` with Podman info, container state, logs, and health endpoint output.

### 6. Tear down the local stack

```bash
make local-down
# or: bash deploy/local/scripts/down-local.sh
```

### 7. Reset the local stack and volumes

```bash
make local-reset
# or: bash deploy/local/scripts/reset-local.sh
```

Use this when you want a clean local state and do not need to preserve the local PostgreSQL or Qdrant volumes.

## Check health manually

```bash
curl http://127.0.0.1:8787/healthz
curl http://127.0.0.1:6333/
```

## Notes for Apple Silicon

- Prefer `arm64` images locally.
- Use Rosetta only when deliberately validating `amd64` compatibility.
- Keep host-local GUI runtimes outside the compose stack at first.

## Local developer workflow

1. Bring up the base stack under Podman.
2. Develop `memoryd` first.
3. Attach LiteLLM and OpenClaw adapters against local `memoryd`.
4. Keep LLM runtimes host-local until the memory plane is stable.

## Local acceptance checks

The local M2 path is acceptable when:

- `memoryd`, PostgreSQL, and Qdrant all come up under `podman compose`;
- `curl http://127.0.0.1:8787/healthz` returns successfully;
- `make local-status` reports healthy services;
- `make local-smoke` returns a recalled item;
- `make local-debug` works if a container fails;
- `make local-down` and `make local-reset` behave as expected.

## Troubleshooting

### Podman machine does not start

Recreate the machine and ensure Podman is current.

### Compose command fails

Install a Compose provider and use `podman compose` rather than assuming Docker Compose is present.

### Qdrant is up but recall is poor

The current embedder is deterministic and local-first. It is for bring-up, not quality benchmarking.

### PostgreSQL connection errors

Check that `MEMORYMESH_STORE_URI` uses the service name `postgres` when running inside compose and `127.0.0.1` only when testing from the host.
