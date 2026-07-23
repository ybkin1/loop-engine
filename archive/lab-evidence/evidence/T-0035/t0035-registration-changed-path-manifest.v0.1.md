# T-0035 Registration Changed-Path Manifest v0.1

Registration-only manifest. Candidate and global Project Governor paths are intentionally absent.

## Exact Changed Paths

- `.ai/tasks/T-0035.md`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/evidence/T-0035/t0035-implementation-gate-request.v0.1.md`
- `.ai/evidence/T-0035/t0035-implementation-decision-packet.v0.1.md`
- `.ai/evidence/T-0035/t0035-registration-changed-path-baseline.v0.1.md`
- `.ai/evidence/T-0035/t0035-implementation-target-protected-boundary-baseline.v0.1.md`
- `.ai/evidence/T-0035/commands.md`
- `.ai/evidence/T-0035/t0035-registration-validation.v0.1.md`
- `.ai/evidence/T-0035/t0035-registration-handoff-audit.v0.1.md`
- `.ai/evidence/T-0035/t0035-registration-changed-path-manifest.v0.1.md`

## Final Registration Fingerprints

| Path | Size | Last write time | SHA-256 |
|---|---:|---|---|
| `.ai/tasks/T-0035.md` | 3682 | `2026-07-18T15:21:27.9624098+08:00` | `9C605F28F43F9B015FEBA82B568E74A92A49B7F64BDF38FF9A7564EA1CC7574D` |
| `.ai/task_graph.yaml` | 10581 | `2026-07-18T15:26:27.0262617+08:00` | `5651189D8BBC78CBBDE20D895102E7D394FEA1F82622C3D502CF8D36F36DAE43` |
| `.ai/gates.yaml` | 281743 | `2026-07-18T15:27:37.0961770+08:00` | `C325E4734D7712C8FF63F7DA7A7C0AEFC8F5ECADE02645FE74ACF63741D3DE56` |
| `.ai/state.yaml` | 8250 | `2026-07-18T15:26:27.0246709+08:00` | `39F0B797A19C170A1BFBDC1B3C0638593F3161A96E4EDB763C726013701537DB` |
| `.ai/HANDOFF.md` | 4753 | `2026-07-18T15:28:17.0828903+08:00` | `8720CFCE3A11CCAB69FB651187F556758950CE6C135612AE264C2103BD78B9CE` |
| `.ai/evidence/T-0035/t0035-implementation-gate-request.v0.1.md` | 1276 | `2026-07-18T15:21:27.9694149+08:00` | `96215ADA1EBBA55128461114881DFC0C27A26600502BBC5473727B1F1BC89327` |
| `.ai/evidence/T-0035/t0035-implementation-decision-packet.v0.1.md` | 12902 | `2026-07-18T15:23:35.7727113+08:00` | `AC37D228177D72280B45F81A90305F8328182A581E694D5802F0117F330713FD` |
| `.ai/evidence/T-0035/t0035-registration-changed-path-baseline.v0.1.md` | 1391 | `2026-07-18T15:24:12.9881459+08:00` | `B4216EF8391A836807196EA654800CB1E0BEFEDDD8C11FCAAF5133B7683F25D2` |
| `.ai/evidence/T-0035/t0035-implementation-target-protected-boundary-baseline.v0.1.md` | 5403 | `2026-07-18T15:25:33.8945944+08:00` | `77E238099C768C4438C7A160538AB07B1AAD4C492B9599DB0C378CC4CB337BD2` |
| `.ai/evidence/T-0035/commands.md` | 1549 | `2026-07-18T15:24:12.9890969+08:00` | `143A1BC2DB56D55389616388BE1B20A1960C5B25A2D24CB972A0BB2C95639F4C` |
| `.ai/evidence/T-0035/t0035-registration-validation.v0.1.md` | 1387 | `2026-07-18T15:29:53.2130341+08:00` | `AE6476BBF0EC58A71941C2BED5A794BAB6C10B7C9540458E7BFB47BBCB6623E0` |
| `.ai/evidence/T-0035/t0035-registration-handoff-audit.v0.1.md` | 688 | `2026-07-18T15:29:53.2150361+08:00` | `F0EEFC8283FDC21D0DEBCDC6E96433CB53BD1BF492C82B7849A632E22455CCF8` |

## Containment Result

`PASS`: all registration writes are within the user-authorized registration paths. No candidate file, global Project Governor file, old task file, or old evidence file changed.

The manifest self-entry is listed but not self-hashed because a file cannot contain its own final SHA-256 without recursion. Its final size/mtime/SHA-256 must be recorded by the next session's independent audit if needed.

## Stop Boundary

Registration stopped before Gate approval and implementation. No downstream task or Gate was created.
