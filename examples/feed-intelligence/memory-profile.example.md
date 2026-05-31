# Feed Intelligence memory profile example

Status: example-only contract

This example applies the existing Slash Topic memory profile posture to the canonical SocioProphet Feed Intelligence reader.

Canonical reader surface:

```text
SocioProphet/socioprophet/socioprophet-web/client-vue
```

Related upstream examples:

```text
SocioProphet/slash-topics/examples/feed-intelligence/scope.example.md
SocioProphet/new-hope/examples/feed-intelligence/membrane-event.example.md
```

## Purpose

MemoryMesh attaches after SlashTopics scope resolution and New Hope membrane admission. The Feed Intelligence reader can display memory posture, but it must not silently write durable memory from feed items, browser captures, annotations, summaries, or graph views.

## Example profile

```yaml
memoryProfileRef: memorymesh-feed-intelligence-profile
slashTopicScope:
  topic: /news/global
  membraneId: new-hope-feed-item-membrane

topologyRoles:
  publicSurfaceRef: slash-topics-public-surface
  runtimeSubstrateRef: new-hope-runtime-substrate
  runtimeAliasRef: slash-topics-runtime-alias
  compatibilityRef: new-hope-compatibility

recallPolicy:
  scope: slash-topic-scoped
  sensitivePayloadStorage: disallowed
  topK: 8
  includeRelations: false
  includeRawEvents: false

writebackPolicy:
  enabled: false
  dryRunMode: no-writeback
  allowedMemoryClasses: []

retention:
  class: feed-intelligence-fixture
  evidenceRequired: true
  ttlDays: 30

redaction:
  enabled: true
  sensitivityThreshold: internal
  redactedFields:
    - excerpt
    - annotationBody
    - browserProfileClass

labProfile:
  embeddingModel: deterministic-local-fixture
  nlpPipeline: fixture-only
  multimodalEnabled: false
  launchLabJobs: false

dryRun:
  enabled: true
  queryRoutingPlan:
    memoryProfileRef: memorymesh-feed-intelligence-profile
    memoryEventRef: memory.dry-run.feed-intelligence.001
    publicSurfaceRef: slash-topics-public-surface
    runtimeSubstrateRef: new-hope-runtime-substrate
    runtimeAliasRef: slash-topics-runtime-alias
    compatibilityRef: new-hope-compatibility

evidenceRefs:
  - eventlog://feed.subscribed/001
  - eventlog://item.normalized/001
  - eventlog://newhope.membrane/001
```

## Boundary rules

- MemoryMesh may provide scoped recall posture after topic and membrane resolution.
- Raw sensitive payload storage remains disallowed by default.
- Dry-run mode performs no recall backend call and no writeback.
- Writeback remains disabled until a later explicit governance flow approves it.
- Feed item display, browser capture, and graph preparation do not imply durable memory promotion.

## Acceptance posture

This example is acceptable while it remains a non-runtime memory-profile example. It must not claim live recall, writeback, promotion, embedding jobs, or durable memory storage.
