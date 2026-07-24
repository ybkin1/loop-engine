# T-0034 Repair Protected Baseline v0.2

Captured before repair writes at `2026-07-16T14:10:13.0486096+08:00`.

## Governance Write-Before Baseline

| Path | SHA-256 | Size |
|---|---|---:|
| `.ai/gates.yaml` | `7F5987A49296D6A345C949EDFA059A71749A7EE79128FAEBFDC80E7BE65F98B9` | 202548 |
| `.ai/state.yaml` | `57F6C3F32A2C4AB49806DEE8291C257C63532DAF12BF6830695B57B76AE0A1E3` | 2245 |
| `.ai/HANDOFF.md` | `80864DF9F4CBC4ACC3D315191DEE519420CDAA2D8CA338E9E35C0F48A2B5D5D6` | 13523 |

## Protected Global Project Governor

| Path | SHA-256 | Size |
|---|---|---:|
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\governor_lib.py` | `7D0344AF52F46DED67F4328A016D17D81A921F4903EA6F126A06D02DD11FACEA` | 19247 |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py` | `28D562B5BB1B80F28589E25DCE355472F058D39C2F94680E309BAB36AEED19D4` | 4828 |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py` | `D8C9834DC77CC208785811647A61AB7A3D2B7FB6D2D866C7B5602C1FF23EC5D2` | 1926 |
| `C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py` | `92DFA111C209CEE7283B1451E947C4E94EB5067A34A8AC9EC97674A78CB12545` | 3529 |

## Protected Isolated Candidate

| Path | SHA-256 | Size |
|---|---|---:|
| `candidates/T-0030-project-governor-repair/BOUNDARY.md` | `C5F24330B13E6A2BF0C2CAE8C8792AA58584433675BFEA4721858E683D1C56EB` | 2639 |
| `candidates/T-0030-project-governor-repair/NOT_ACTIVATED` | `9BBB093D9C5E6129B1CE440575E9D289366FCDC7223C944532376D0C2E033EAE` | 178 |
| `candidates/T-0030-project-governor-repair/NOT_INSTALLED` | `CA19715176E4FD328515F5ECD36D1EB7B91AF7C70BC767C3F61EF9A52B2AB7E5` | 187 |
| `candidates/T-0030-project-governor-repair/PROVENANCE.yaml` | `648550FB2D02B121C5740AA611C7ADC74769D243451C5D5D955E72AB6918011C` | 5219 |
| `candidates/T-0030-project-governor-repair/scripts/audit_handoff.py` | `92DFA111C209CEE7283B1451E947C4E94EB5067A34A8AC9EC97674A78CB12545` | 3529 |
| `candidates/T-0030-project-governor-repair/scripts/close_session.py` | `28D562B5BB1B80F28589E25DCE355472F058D39C2F94680E309BAB36AEED19D4` | 4828 |
| `candidates/T-0030-project-governor-repair/scripts/governor_lib.py` | `7D0344AF52F46DED67F4328A016D17D81A921F4903EA6F126A06D02DD11FACEA` | 19247 |
| `candidates/T-0030-project-governor-repair/scripts/validate_state.py` | `D8C9834DC77CC208785811647A61AB7A3D2B7FB6D2D866C7B5602C1FF23EC5D2` | 1926 |
| `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py` | `ED22E7DCBFF310EB91AFB9713A2076E7C7140C77C37CEA418794E87717C77385` | 13152 |

Candidate invariant: exactly nine files, directories limited to root, `scripts`, and `tests`; zero `__pycache__`, `.pyc`, or `.pyo`; `NOT_INSTALLED` and `NOT_ACTIVATED` remain present.

## Immutable T-0034 Evidence

The complete 15-file path/size/full-SHA-256 manifest in `t0034-design-repair-changed-path-baseline.v0.2.md` is incorporated by reference and must match disk exactly.

## Target Absence

All fourteen v0.2 repair targets named by the Gate were absent before execution. No independent-review artifact path was authorized or created.

Any protected mismatch requires immediate stop and `BLOCKED` or `SCOPE_VIOLATION`; destructive recovery requires a separate user decision.
