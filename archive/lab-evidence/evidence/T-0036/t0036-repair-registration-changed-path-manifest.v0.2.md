# T-0036 Repair Gate Revision Changed-path Manifest v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

## Modified Governance Projection

| Path | Pre-revision SHA-256 | Post-revision SHA-256 | Post size | Post mtime_ns |
|---|---|---|---:|---:|
| `.ai/gates.yaml` | `2FE54C90C580156A1D6E0B103041EA15D0E076BF311C6FF8637DEFE859F9256F` | `13D6649D76EC63455F164ACB859570BBDA0897D8E7E890F550FAE6C2FF095B38` | 308523 | 1784522519954087200 |
| `.ai/state.yaml` | `42B87B02793F9CD46D5A27BD67E71AA6FEB24862383299A632BF0DEE47CAF6BD` | `1E64E1147065B7FB31B3969E72B8FDF838BD91637764A97852FABE1A6FD861C9` | 11409 | 1784521729766866200 |
| `.ai/task_graph.yaml` | `51E38F9308722C3F4EECE5996598870AB1545F4EFCD2327AE137B0D9251EB528` | `A6BCF589BCDA23163834E897A2B020F85BE5F22AC0AB30BA74B40841097A0DC6` | 11119 | 1784521661310325200 |
| `.ai/tasks/T-0036.md` | `6D5538B5C4CBE48D3F294849056F51AF9E524117B8ECB45232ED95A6CB51F923` | `5DFB800C2A0B44185269394E1B8FC3D04E409F1D9581518680CFE107F72765D8` | 7368 | 1784521275910600000 |
| `.ai/HANDOFF.md` | `75B0F2CBC47655E0CA0BEFE41080B5059FCEF91C5B80E3765C71A25460B208C3` | `C4A822723E6E758E9CE3725AA70C120E8BAEB4C9D00436871738128E19EB6A3E` | 7609 | 1784522185331010300 |

## New Additive v0.2 Evidence

| Path | SHA-256 | Size | mtime_ns |
|---|---|---:|---:|
| `.ai/evidence/T-0036/t0036-repair-gate-request.v0.2.md` | `A020C34CD2A61FAA9697AB8E8A9E28A7743E7792FDC5EFC912530625575F33C0` | 1817 | 1784521234986726100 |
| `.ai/evidence/T-0036/t0036-repair-decision-packet.v0.2.md` | `FF96253EC7ABDFC06F11F62D567B41DA417A1C93DF15C4825274A81CC9CFFC5F` | 8801 | 1784522519948085600 |
| `.ai/evidence/T-0036/t0036-repair-test-plan.v0.2.md` | `C34224F7910D757511C83325EF336317E7CA45AE1B807BB1C1C97CA75BA5BB41` | 6229 | 1784522519950085200 |
| `.ai/evidence/T-0036/t0036-repair-structured-state-contracts.v0.2.md` | `0CC76D0B01899EA8589599B2E853D5D24C3D5C9245F1F6E28155F2FEE2CDF186` | 11350 | 1784522519947082600 |
| `.ai/evidence/T-0036/t0036-repair-candidate-and-protected-baseline.v0.2.yaml` | `C4BD1BE4D91F9AE9092D1E703A6C40A5441ABFD4AB017C8F806884508A8FDC95` | 2995 | 1784521087582046700 |
| `.ai/evidence/T-0036/t0036-repair-registration-commands.v0.2.md` | `1B1985B71DADA5A83B2D75474FE72A618A5D47E72CC53B16432BC14475F9EE95` | 1926 | 1784521810198696200 |
| `.ai/evidence/T-0036/t0036-repair-registration-validation.v0.2.md` | `6A7D0555B25E3FC352FB9E777F9EBEFCAF54F656F0235CE4E6C94E0F7AA29740` | 4162 | 1784522519950085200 |

This manifest does not embed its own hash; final mechanical validation recomputes it externally.

## Protected And Forbidden Result

- Effective protected baseline: 43 subjects, including the four new read-only project sources.
- Candidate code/test writes: `0`.
- `.ai/PROJECT.md` / `.ai/CONTRACTS.md` writes: `0`.
- T-0034 PCC/CDFT contract writes: `0`.
- Live `.ai/project_continuity.yaml` / `.ai/transaction_registry.yaml` creation or modification: `0`.
- Global Project Governor / `AGENTS.md` / marker writes: `0`.
- Gate approval or repair execution: `0`.
- T-0037, installation, activation, runtime, or real-project effects: `0`.

Pre-existing uncommitted T-0035/T-0036 worktree paths remain preserved. This manifest classifies only the v0.2 revision writes above.
