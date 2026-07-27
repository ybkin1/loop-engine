# Host Adapter Contract

- Host: `Codex | Claude Code | Zcode | Qoder | other`
- Adapter version:
- Host version:
- Enforcement level: `HARD | PARTIAL | ADVISORY`
- Capability source:

## Capability matrix

| Capability | Available | Deterministic | Permission | Evidence | Fallback |
| --- | --- | --- | --- | --- | --- |
| filesystem read/write |  |  |  |  |  |
| command execution |  |  |  |  |  |
| independent agent |  |  |  |  |  |
| structured output |  |  |  |  |  |
| human Gate |  |  |  |  |  |

## Forbidden assumptions

- A prompt cannot create a missing permission.
- A host report cannot be treated as an independent verifier without provenance.
- Unsupported hard constraints must downgrade enforcement or block the route.
