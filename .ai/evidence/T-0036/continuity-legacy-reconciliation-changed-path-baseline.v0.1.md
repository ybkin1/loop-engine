# T-0036 Pre-Rereview Continuity And Legacy Reconciliation Baseline v0.1

Recorded at: `2026-07-24T15:05:09+08:00`

This is the byte-level pre-registration baseline for the future execution allowlist. `absent` means the path did not exist when this Gate was prepared. Existing user changes are preserved; this record does not claim authorship of them.

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/HANDOFF.md` | 18547 | `FD1E85A100AAAE311B598BA80F1B100CCF6939B0EE1CBBAFC0140274B6B9DBF5` |
| `.ai/state.yaml` | 11301 | `21C337E3B98C7C53D21A1E0932F6D2F75E0B546652F01EC8C1FCD9ECF8F71717` |
| `.ai/task_graph.yaml` | 11308 | `4CA4545488D7AA7AC0CA178ACA59E9A8C2286C94B27EB24A230D42ACE537A36F` |
| `.ai/tasks/T-0035.md` | 2534 | `52753002094632330583CD1DF115A0B5C4E16FAC7D1B6C4AFE277CD4F1F4790F` |
| `.ai/tasks/T-0036.md` | 5197 | `8C6AA590D49C7C8AFC60B5A90286DC173C3307F390E424926530CDF395A89224` |
| `.ai/DECISIONS.md` | 12268 | `2D4BCA2AC559DE3227B570FB73DFE6CF096BB3F5B1E3A6F66157DEE5A7044E12` |
| `.ai/KNOWN_ISSUES.md` | 1638 | `BEFBC100268EA7585FC4971C9E5E2865D0FDDDF66983931504C5345CF9ED277C` |
| `.ai/PROGRESS.md` | 34801 | `A2FC93EF8500D9E83F18D55F42AFB7F1E94451B1290A33B169A7BAD7F40C67C3` |
| `.ai/gates.yaml` | 317420 | `384BE868AE8C196539482B4CECE74A9B38BD31FA14D57FD32A755D5D58A64681` |
| `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md` | 9870 | `13BAD8A6774694876CE7C543BD6615062FA6A5E9BE88D0CCFA07F4D156B2E534` |
| `.ai/evidence/T-0036/continuity-legacy-reconciliation-execution-commands.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/continuity-legacy-reconciliation-validation.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/continuity-legacy-reconciliation-changed-path-manifest.v0.1.md` | absent | absent |
| `.ai/evidence/T-0036/t0035-administrative-closeout-validation.v0.1.md` | absent | absent |

Startup worktree baseline: `git status --porcelain -uall` was non-clean and included pre-existing changes across governance, candidate, material-library, Loop candidate, docs, tests, and evidence paths. `git diff --check` returned exit code `0`. Future execution must preserve unrelated changes and prove its changed paths are a strict subset of the exact allowlist.
