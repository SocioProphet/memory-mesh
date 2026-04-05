# Deployment decision matrix

| Question | Local M2 Podman | GKE review | Cloud Run alternative |
|---|---|---|---|
| Best for day-to-day development | Yes | No | No |
| Preserves stateful topology | Partially | Yes | No |
| Works naturally with Apple Silicon | Yes | Yes, with multi-arch images | Indirectly; deploy target is amd64 |
| Best for shared review | Limited | Yes | Sometimes |
| Best for quick public ingress | No | Sometimes | Yes |
| Recommended default | Yes | Yes | No |

## Default answer

- develop locally on the M2 Mac with Podman;
- review in Google Cloud on GKE Autopilot;
- use Cloud Run only for stateless or demo-oriented edge services.
