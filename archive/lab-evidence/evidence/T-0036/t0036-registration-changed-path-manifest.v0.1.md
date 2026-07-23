# T-0036 Registration Changed-path Manifest v0.1

## Result

`PASS_REGISTRATION_CONTAINMENT`

All T-0036 registration writes are inside the exact user-authorized registration list. No candidate, global Project Governor, `AGENTS.md`, T-0035, old evidence, environment, installation, activation, runtime, or downstream path was modified by this registration.

## Registration Paths

- `.ai/tasks/T-0036.md`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/evidence/T-0036/t0036-review-gate-request.v0.1.md`
- `.ai/evidence/T-0036/t0036-review-decision-packet.v0.1.md`
- `.ai/evidence/T-0036/t0036-review-subject-freeze-manifest.v0.1.md`
- `.ai/evidence/T-0036/t0036-preliminary-finding-leads.v0.1.md`
- `.ai/evidence/T-0036/t0036-registration-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0036/commands.md`
- `.ai/evidence/T-0036/t0036-registration-validation.v0.1.md`
- `.ai/evidence/T-0036/t0036-registration-handoff-audit.v0.1.md`
- `.ai/evidence/T-0036/t0036-registration-changed-path-manifest.v0.1.md`

## Stable Registration Fingerprints

| Path | Size | SHA-256 |
|---|---:|---|
| `.ai/tasks/T-0036.md` | 4340 | `13DD4555A1B811775D99EC5A26DFD29E659092F521DF0FF02A77082487B42F96` |
| `.ai/task_graph.yaml` | 11123 | `D8EAF1D093E2939B4E9E79D3E5C767F44B93279E8EB32E3BCBF917D02AC5A29A` |
| `.ai/gates.yaml` | 290524 | `64838E53F130E831543D24587CE78DEDD8071329E0EF371B2A5F4C4A6A170E64` |
| `.ai/state.yaml` | 8929 | `EC5C1D10459FB98703934B1DE1CA56A9C1979D11DA5E4D352D9C301BD51287B8` |
| `.ai/evidence/T-0036/t0036-review-gate-request.v0.1.md` | 2701 | `9461FD4A5902EC916D885CC6D994C3D46C19C2B5CB9A925E7A66BE62E28150F7` |
| `.ai/evidence/T-0036/t0036-review-decision-packet.v0.1.md` | 3109 | `15F7EB65A68DA0F3887FED06C0DBBF181C8A4D7AD7D5E619ED827CFF0A95E19F` |
| `.ai/evidence/T-0036/t0036-review-subject-freeze-manifest.v0.1.md` | 13113 | `1C0E847C51DA2F01CCF451A23989D59EEEC89C34696E0ACA77920A226219DAF3` |
| `.ai/evidence/T-0036/t0036-preliminary-finding-leads.v0.1.md` | 2427 | `43E2792C3742509C60AB0BE38191EAE3503A3AA51E8A9DC418166FB6EECB3951` |
| `.ai/evidence/T-0036/t0036-registration-changed-path-baseline.v0.1.md` | 1611 | `621C4BBACF45E635357DE760B25E22F4923FF4223B26EB4C3386B0DAD6D59CA0` |
| `.ai/evidence/T-0036/commands.md` | 2136 | `36DDE61BCB891D7DF394D14A3BCE620BC4DD5E36ECA9FAC1EB63C6F9150D4C09` |
| `.ai/evidence/T-0036/t0036-registration-validation.v0.1.md` | 953 | `19327812074387C8017F9027C04872FC0D90865A091561ACD205D285E11B367E` |
| `.ai/evidence/T-0036/t0036-registration-handoff-audit.v0.1.md` | 802 | `6DF2AC2665529128579ED5DBD606045ED6475CDE8EA797DC96F6C75D0536C2D3` |

`.ai/HANDOFF.md` is the final governance projection and this manifest is self-referential evidence. Their own hashes are intentionally not embedded here; HANDOFF is audited after final rendering, and this manifest is verified by path containment plus the T-0036 evidence-manifest hash in the stable checkpoint.

## Protected Recheck

- Freeze rows checked: `60`; mismatches: `0`.
- Logical T-0035 Gate canonical JSON SHA-256: `1341D1E79A1D0715BEF7E1820ABEC5CFBE75EF75697E302F6FD6902892B57F63`; unchanged.
- T-0035 Gate canonical JSON bytes/fields: `11102` / `63`; unchanged.
- Candidate inventory: 10 files, 2 directories, 0 cache/compiled artifacts, 0 reparse points.
- Candidate PATH/PYTHONPATH entries: 0 / 0.
- `git diff --check`: pass.

Existing T-0035 worktree changes were present in the registration baseline and were not reverted or attributed to T-0036.
