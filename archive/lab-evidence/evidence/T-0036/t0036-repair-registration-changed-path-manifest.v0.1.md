# T-0036 Repair Gate Registration Changed-path Manifest v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

## Modified Governance Projection

| Path | Pre-write SHA-256 | Post-write SHA-256 | Post size | Post mtime_ns |
|---|---|---|---:|---:|
| `.ai/gates.yaml` | `BF42782E94A57739583D324043F8B6FFE6A1BF72A94DD9093523446C8A570884` | `2FE54C90C580156A1D6E0B103041EA15D0E076BF311C6FF8637DEFE859F9256F` | 302117 | 1784520057333237300 |
| `.ai/state.yaml` | `BA3D0AE9838AF613C1FB48B24AD940BCF0D53D910FF590E6638695F653FB0ECE` | `42B87B02793F9CD46D5A27BD67E71AA6FEB24862383299A632BF0DEE47CAF6BD` | 11116 | 1784519688412062800 |
| `.ai/task_graph.yaml` | `0A19D0DB81D113399F702E649AE9A3F60636F11C6A1EFAF593097941EB1A9C8A` | `51E38F9308722C3F4EECE5996598870AB1545F4EFCD2327AE137B0D9251EB528` | 11093 | 1784519528850002300 |
| `.ai/tasks/T-0036.md` | `C6CAA6469170BF8E860017DA97FDABA11D40DAF1CF605C635ECC4382B5B4355D` | `6D5538B5C4CBE48D3F294849056F51AF9E524117B8ECB45232ED95A6CB51F923` | 6444 | 1784519605159179100 |
| `.ai/HANDOFF.md` | `3B0D5778959E1BC672D34B9F49EE4F6C51AE2B88160946A4F0ED714655DC9324` | `75B0F2CBC47655E0CA0BEFE41080B5059FCEF91C5B80E3765C71A25460B208C3` | 6099 | 1784519776049614100 |

## New Additive Evidence

| Path | SHA-256 | Size | mtime_ns |
|---|---|---:|---:|
| `.ai/evidence/T-0036/t0036-repair-gate-request.v0.1.md` | `F498FEC0BFB51848A17EF139928E196CA4F7DEAD1F9155022D4999EF3EA3264F` | 2012 | 1784519379356810400 |
| `.ai/evidence/T-0036/t0036-repair-decision-packet.v0.1.md` | `A5129998A359C3981080EA9532F99DEC5324244067FFF45F39266BB56D7B6EA8` | 19095 | 1784519270757522900 |
| `.ai/evidence/T-0036/t0036-repair-test-plan.v0.1.md` | `6D0EA9F3C4FA0BBE0579BF352CACF98CDC4881CEAEEBC0165642972C8800F769` | 8549 | 1784519327581384400 |
| `.ai/evidence/T-0036/t0036-repair-candidate-and-protected-baseline.v0.1.yaml` | `6B0B7D1B449D59C2DB18510760463F3323ECCDA1DAA4B51D9F485F2BAC0F7688` | 10182 | 1784519890800322400 |
| `.ai/evidence/T-0036/t0036-repair-registration-commands.v0.1.md` | `4878F0234B72D192A1BDBB5E65C680C965A8D0E7A7F7F94488473292E8F2843D` | 2826 | 1784519944190760400 |
| `.ai/evidence/T-0036/t0036-repair-registration-validation.v0.1.md` | `C689D3441D73D17DD19D05076116F04462D760370A4C16A286A643730E0E6E72` | 2794 | 1784520020553183000 |

This manifest does not embed its own hash. Its final hash is recomputed by the post-write mechanical check.

## Boundary Result

- Candidate files changed by registration: `0`.
- Candidate tests changed by registration: `0`.
- Global Project Governor files changed by registration: `0`.
- `AGENTS.md` changed by registration: `0`.
- `NOT_INSTALLED` / `NOT_ACTIVATED` changed by registration: `0`.
- T-0037 created: `false`.
- Installation, activation, runtime enablement, or real-project effect: `false`.

The project worktree contained pre-existing T-0035/T-0036 uncommitted paths before this registration. This manifest identifies the bounded registration writes by pre-write fingerprints and exact new filenames; it does not classify unrelated existing dirty paths as registration changes.
