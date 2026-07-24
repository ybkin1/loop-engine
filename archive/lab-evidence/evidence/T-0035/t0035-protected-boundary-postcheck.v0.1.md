# T-0035 Protected Boundary Postcheck v0.1

Checked after final manifest bind at `2026-07-18T17:09:31.1870250+08:00`.

Result: `PASS`

- Final manifest schema/status: `FinalValidationManifest/v1` / `bound`.
- Final manifest fingerprints: `37`; mismatches: `0`.
- Target/test fingerprints: `8/8` match SHA-256, size, and `mtime_ns`.
- Protected fingerprints: `29/29` match SHA-256, size, and `mtime_ns`.
- Candidate inventory: `10` files, `2` directories.
- Candidate reparse points: `0`.
- Candidate cache/compiled artifacts: `0`.
- Candidate root in `PATH`: `0` entries.
- Candidate root in `PYTHONPATH`: `0` entries.
- Postcheck `PATH` SHA-256: `D51DDF92E46FCAD4A286A5919F37A22B9D12C9C9C29F955D0B3D9D7E61121BE7` (matches preflight).
- Postcheck `PYTHONPATH` SHA-256: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` (matches preflight).
- `NOT_INSTALLED`, `NOT_ACTIVATED`, `AGENTS.md`, and all protected global Project Governor files are bound in the final manifest and unchanged.
- Git changed-path scope violations: `0`.
- `git diff --check`: passes after mechanical HANDOFF trailing-space removal.

No persistent environment, discovery, startup, import, hook, plugin, skill, MCP, automation, protocol, installation, or activation state changed.
