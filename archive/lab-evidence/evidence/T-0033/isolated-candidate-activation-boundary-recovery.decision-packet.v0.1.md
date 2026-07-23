# T-0033 Isolated Candidate And Activation-Boundary Recovery Decision Packet

## Decision

Decide whether a later, separate execution turn may establish an isolated Project Governor candidate without changing the currently active global source paths.

- Gate: `G-T-0033-ESTABLISH-ISOLATED-CANDIDATE-RESTORE-ACTIVATION-BOUNDARY`
- Candidate root: `C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair`
- Global source root: `C:\Users\Administrator\.codex\skills\project-governor\`

The candidate root is plan data only while this gate is pending. It has not been created.

## Exact Future Copy Set

| Source | SHA-256 | Size | Last write time | Candidate relative target |
|---|---|---:|---|---|
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\governor_lib.py` | `7D0344AF52F46DED67F4328A016D17D81A921F4903EA6F126A06D02DD11FACEA` | 19247 | `2026-07-13T18:48:34.2268725+08:00` | `scripts/governor_lib.py` |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py` | `28D562B5BB1B80F28589E25DCE355472F058D39C2F94680E309BAB36AEED19D4` | 4828 | `2026-07-13T18:40:46.0898646+08:00` | `scripts/close_session.py` |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py` | `D8C9834DC77CC208785811647A61AB7A3D2B7FB6D2D866C7B5602C1FF23EC5D2` | 1926 | `2026-07-13T18:41:16.9168048+08:00` | `scripts/validate_state.py` |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py` | `92DFA111C209CEE7283B1451E947C4E94EB5067A34A8AC9EC97674A78CB12545` | 3529 | `2026-07-13T18:54:19.0955547+08:00` | `scripts/audit_handoff.py` |
| `C:\Users\Administrator\.codex\loop-engine-lab\.ai\evidence\T-0030\test_project_governor_consistency.py` | `ED22E7DCBFF310EB91AFB9713A2076E7C7140C77C37CEA418794E87717C77385` | 13152 | `2026-07-13T18:51:07.6950792+08:00` | `tests/test_project_governor_consistency.py` |

The four scripts are the exact T-0030 implementation targets. The preserved T-0030 regression test is the only auxiliary test required in the candidate. No other test or helper file is authorized for copying by this gate.

## Candidate-Only Records To Create During Future Execution

- `PROVENANCE.yaml`: source path, source hash, size, timestamp, candidate path, copy timestamp, and copied-file hash for each item.
- `NOT_INSTALLED`: explicit marker that no installation occurred.
- `NOT_ACTIVATED`: explicit marker that no activation occurred.
- `BOUNDARY.md`: records that the candidate is not on `PATH`, `PYTHONPATH`, Codex startup loading, global imports, tool discovery, hooks, plugins, skills, MCP, automation, or protocols.

These records are future T-0033 execution outputs, not files created in the current gate-registration turn.

## Files Explicitly Forbidden From The Candidate

- `AGENTS.md`, user or project configuration, secrets, credentials, tokens, caches, logs, backups, compiled files, and unrelated evidence.
- Any file from `C:\Users\Administrator\.codex\skills\project-governor\` other than the four exact scripts listed above.
- Any modified test, repaired script, generated wrapper, symlink, junction, launcher, import hook, plugin, MCP definition, automation, protocol, or activation artifact.

## Activation-Boundary Verification Plan

Future execution must:

1. Recompute every source hash before copying and stop on any mismatch.
2. Copy only through literal source and destination paths under the candidate root.
3. Verify copied hashes equal their source hashes.
4. Run candidate tests only by explicitly setting the working directory or import path to the candidate, without changing persistent environment variables or Codex configuration.
5. Recompute all four global script hashes after candidate checks and require exact equality with the pre-execution baseline.
6. Verify the candidate root is absent from `PATH`, `PYTHONPATH`, configured skill roots, startup loading, global import resolution, and tool discovery.
7. Verify there are no symlinks, junctions, path replacements, or renamed global targets connecting the candidate to the live runtime.

Representative read-only checks after future creation:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '<exact-global-or-candidate-file>'
Get-Item -LiteralPath '<exact-file>' | Select-Object FullName,Length,LastWriteTime
$env:PATH -split ';'
$env:PYTHONPATH
Get-ChildItem -LiteralPath 'C:\Users\Administrator\.codex\skills\project-governor\scripts' -Force
```

Candidate test execution must use explicit candidate paths and must not call the globally discovered Project Governor commands implicitly.

## Failure Recovery And Rollback Boundary

- Before the candidate exists, failure recovery is to stop without changing any source or runtime path.
- If a future copy is partial or a hash differs, stop, preserve evidence, and request a separate recovery decision before deleting or replacing anything.
- T-0033 rollback is limited to the newly created candidate tree and requires a separate explicit recovery authorization if destructive removal is needed.
- The global scripts must never be overwritten, rolled back, deleted, renamed, stopped, reinstalled, or treated as retroactively authorized by T-0033.
- Original T-0030, T-0031, and T-0032 evidence remains immutable.

## Downstream Boundaries

- T-0034 is design-only: define the HANDOFF continuity contract and writing standard. It may not modify candidate code.
- T-0035 may implement the T-0030 repair only inside the isolated candidate and only after the separately approved T-0034 design is available as input.
- T-0036 independent review, T-0037 installation, T-0038 activation, and T-0039 reverification each require separate tasks and gates.

## Risk Review

- The primary risk is confusing candidate creation with installation or activation.
- A copied candidate may be accidentally imported if environment or discovery paths are changed; such changes are prohibited.
- Approval may be misread as execution; a later explicit execution request is still required.
- Tests, validators, audits, reviews, subagents, and AI recommendations are evidence only and do not approve this gate.
