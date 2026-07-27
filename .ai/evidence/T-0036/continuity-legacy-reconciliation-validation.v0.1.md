# T-0036 Continuity And Legacy Reconciliation Validation v0.1

Gate: `G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1`

Verdict: `reconciliation_completed_awaiting_separate_fresh_rereview_gate`

## Acceptance

| check | result |
| --- | --- |
| T-0035 task status | `completed` |
| T-0035 task-graph status | `completed` |
| T-0035 closeout evidence | present; content Acceptance reproduced |
| administrative boundary | explicit; not product PASS, user acceptance, Runtime implementation, installation, or activation |
| old T-0035..T-0039 mapping | explicitly superseded in current decisions/progress; historical roadmap preserved |
| unresolved old program | registered as unassigned future work; not claimed complete |
| candidate-path verification gap | registered open; not repaired |
| freeze subject disk matches | `65/65` before and after |
| freeze triples aggregate SHA-256 | `02D30F57D71291BB9454D84E0048F137B39813F1749777C8A1EFFE51A352E050` before and after |
| freeze prose ASCII `?` count | `82 -> 0` |
| historical roadmap fingerprint | size `4282`, SHA-256 `1949EED355B3F87C8322B150811EABD959FE0837A35C1E6FA1CCB1FF89C71146`, unchanged |
| candidate/global four-script fingerprints | unchanged from execution preflight |
| YAML parse | PASS |
| `validate_state.py` | PASS |
| `audit_handoff.py` | PASS |
| `git diff --check` | PASS |
| execution changed paths | strict subset of the exact 14-path allowlist |

## HANDOFF Reconciliation

- F-001..F-006 are recorded as deterministically repaired and awaiting fresh independent rereview.
- The completed full-suite fixture repair records `41 passed, 5 subtests passed`; the old six-failure statement is removed.
- Allowed Scope permits only preparation of a separate fresh independent rereview Gate; it does not execute rereview.
- The old 58-file freeze remains historical; the current rereview baseline is the verified 65-subject post-repair freeze.
- Candidate-path verification remains explicitly unverified.

## Candidate Verification Boundary

The candidate consistency test still hard-codes global `SCRIPTS` and `TEMPLATES`. Therefore existing `13 passed` and repository `41 passed` evidence validates current global-script behavior, not the isolated candidate. No candidate test/script or global Project Governor file changed. A later candidate-path verification repair requires a separate Gate.

## Scope And History Proof

- All writes made by this execution are members of the Gate's exact allowlist.
- The 65 frozen subject paths, sizes, and SHA-256 values are unchanged and still match disk.
- `.ai/evidence/T-0034/downstream-program-plan.v0.1.md` remains byte-identical; supersession is additive current governance, not historical rewriting.
- Existing user dirty-worktree changes were preserved.

## Changed-Path Proof

Actual changed set: `13/14`, a strict subset of the exact execution allowlist. The optional standalone changed-path-manifest path remains absent; this validation file is the changed-path evidence.

| path | before size / SHA-256 | after size / SHA-256 |
| --- | --- | --- |
| `.ai/HANDOFF.md` | `18427` / `FE5C1DEF66F1DDEE3A1A2647B15CEF1FEDD0885801E1E16A57921A6631119A86` | `18428` / `7D91FA88B800479BB5E939918F591CD0F853388A759BFAB255424A8CCBDC9B6C` |
| `.ai/state.yaml` | `11957` / `267F04CEE5B55A44EDE7968B6AB6C39E8EAD35541ED256C383B117ECE26482D0` | `12332` / `02D609C4489DD3EE55D86866F63500C63730D8432DA4F3A507AA7005EBBF3865` |
| `.ai/task_graph.yaml` | `11308` / `4CA4545488D7AA7AC0CA178ACA59E9A8C2286C94B27EB24A230D42ACE537A36F` | `11490` / `94DC8AD16905EE6CAF2DD2679D764578D3762FADB702F67B89C79D3022C5F278` |
| `.ai/tasks/T-0035.md` | `2534` / `52753002094632330583CD1DF115A0B5C4E16FAC7D1B6C4AFE277CD4F1F4790F` | `2788` / `D681B6A756F45533C10941C3E1619EDBACE9C103192C85FE642DF889EB564D38` |
| `.ai/tasks/T-0036.md` | `5197` / `8C6AA590D49C7C8AFC60B5A90286DC173C3307F390E424926530CDF395A89224` | `5647` / `27FA02DFEB80BA045F70F6A0F03C41588805281ADEDE521CF9C64C262F23F777` |
| `.ai/DECISIONS.md` | `12268` / `2D4BCA2AC559DE3227B570FB73DFE6CF096BB3F5B1E3A6F66157DEE5A7044E12` | `12762` / `7773880CC4A0966754B56B6C1041AB9CF15E65AA9A697DEF3112C775C332AA9E` |
| `.ai/KNOWN_ISSUES.md` | `1638` / `BEFBC100268EA7585FC4971C9E5E2865D0FDDDF66983931504C5345CF9ED277C` | `2067` / `898CC124E55831C76E390D7F31AD1F82004F64759DD624BB2FCAEE98E984FFFE` |
| `.ai/PROGRESS.md` | `34801` / `A2FC93EF8500D9E83F18D55F42AFB7F1E94451B1290A33B169A7BAD7F40C67C3` | `35262` / `289D16D8419FEFC7EE540835F86C5317DCC577A6060607D19D8860FD9DC03BB2` |
| `.ai/gates.yaml` | `322835` / `7687540F569F6A79788F90FDF5455BBE541354B4BFC31C0AFACC47107D5C7220` | `323812` / `B35D10E81B7CFFE213257078B33BBDF78F61BD87D19CFEFB137315D85496B917` |
| `material-library-repair-freeze-manifest.v0.1.md` | `9870` / `13BAD8A6774694876CE7C543BD6615062FA6A5E9BE88D0CCFA07F4D156B2E534` | `10029` / `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F` |
| `continuity-legacy-reconciliation-execution-commands.v0.1.md` | absent | `3212` / `26382D1C506DB7EE21AF177213BD5C748C69598040077ECFAAA2FE4213B7347E` |
| `t0035-administrative-closeout-validation.v0.1.md` | absent | `2244` / `8F4AE5C0E236D22390CFC9B80E2890AF85D8333D8B44D5D21DB42255A38461D4` |
| `continuity-legacy-reconciliation-validation.v0.1.md` | absent | generated; self-hash intentionally excluded to avoid recursive evidence mutation |

Unchanged allowlist member: `.ai/evidence/T-0036/continuity-legacy-reconciliation-changed-path-manifest.v0.1.md` remains absent.

## Boundary

This evidence is governance reconciliation validation only. It is not T-0036 fresh independent rereview, candidate-baseline acceptance, version freeze, T-0037 review, installation, activation, Host Integration, deployment, or real-project authorization. Execution stops here.
