#!/usr/bin/env node
/**
 * Validate the prophet-mesh memory-scope mirror contract.
 * Lane G — confirms the mirror is structurally sound and cross-repo refs are present.
 */
import { readFile } from 'fs/promises'
import { fileURLToPath } from 'url'

const CONTRACT_PATH = 'contracts/prophet-mesh/prophet-mesh-memory-scope.v0.1.json'
const REQUIRED_FIELDS = [
  'schemaVersion', 'kind', 'contractVersion', 'mirrorId',
  'sourceAuthority', 'mirrorAuthority', 'scopePolicy',
  'privatePreviewInvariants', 'nonProductionBoundary', 'crossRepoTraceability'
]
const REQUIRED_INVARIANTS = [
  'execution_trace_must_include_memory_scope',
  'memory_scope_must_be_explicit',
  'memory_scope_must_not_be_empty_string'
]
const REQUIRED_MODES = ['dry_run_receipt_preview', 'receipt_only']

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function main() {
  const raw = await readFile(CONTRACT_PATH, 'utf8')
  const contract = JSON.parse(raw)

  for (const field of REQUIRED_FIELDS) {
    assert(field in contract, `missing required field: ${field}`)
  }

  assert(contract.kind === 'CrossRepoScopeMirror', 'kind must be CrossRepoScopeMirror')
  assert(contract.contractVersion === 'v0.1', 'contractVersion must be v0.1')

  const policy = contract.scopePolicy
  assert(policy.requiredField === 'execution_trace.memory_scope', 'scopePolicy.requiredField must be execution_trace.memory_scope')
  assert(policy.enforcement === 'reject_if_absent_or_empty', 'scopePolicy.enforcement must be reject_if_absent_or_empty')
  assert(policy.effectBoundary.effectEnabled === false, 'effectBoundary.effectEnabled must be false')
  assert(policy.effectBoundary.workspaceWriteEnabled === false, 'effectBoundary.workspaceWriteEnabled must be false')

  for (const invariant of REQUIRED_INVARIANTS) {
    assert(
      contract.privatePreviewInvariants.includes(invariant),
      `missing required invariant: ${invariant}`
    )
  }

  const boundary = contract.nonProductionBoundary
  for (const mode of REQUIRED_MODES) {
    assert(boundary.coveredModes.includes(mode), `nonProductionBoundary.coveredModes must include ${mode}`)
  }
  assert(!boundary.coveredModes.includes('live_execution'), 'live_execution must not be in coveredModes')

  const trace = contract.crossRepoTraceability
  assert(typeof trace.prophetMeshAdapterRef === 'object', 'crossRepoTraceability.prophetMeshAdapterRef required')
  const ref = trace.prophetMeshAdapterRef
  assert(ref.repo === 'SocioProphet/agentplane', 'adapter ref repo must be SocioProphet/agentplane')
  assert(typeof ref.contentSha256 === 'string' && ref.contentSha256.length === 64, 'contentSha256 must be 64-char hex')
  assert(ref.mode === 'dry_run_receipt_preview', 'adapter ref mode must be dry_run_receipt_preview')

  console.log(JSON.stringify({
    ok: true,
    contractPath: CONTRACT_PATH,
    mirrorId: contract.mirrorId,
    scopePolicy: contract.scopePolicy.enforcement,
    invariantsVerified: REQUIRED_INVARIANTS.length,
    adapterRefSha256: ref.contentSha256.slice(0, 16) + '...',
    nonProductionBoundary: boundary.coveredModes
  }, null, 2))
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  // already runs via top-level await equivalent above
}
