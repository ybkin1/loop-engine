# T-0034 Fresh L0 Review Commands v0.1

## Execution Request

Exact user message: `执行已批准的 G-T-0034-FRESH-INDEPENDENT-L0-READ-ONLY-REVIEW-V0-2`

## Commands And Exit Codes

1. Startup governance validation:

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Exit `2`; only six preserved historical mismatches were reported.

2. Frozen subject admission: PowerShell `Get-Item` and `Get-FileHash -Algorithm SHA256` over all fourteen subjects.

Exit `0`; `14/14` path, size, and SHA-256 checks passed. All four review outputs were absent. Protected task and graph baselines were captured.

3. Canonical and subject reads: PowerShell `Get-Content -Encoding utf8`, `Select-String`, and `rg` over canonical project/task/governance records and frozen artifacts.

Most reads exited `0`. One auxiliary command using `rg ... .ai/evidence/T-0034/*v0.2.md` exited `1` because Windows rejected the wildcard path syntax; it wrote nothing and was replaced by independent Python enumeration.

4. Independent structural checker: inline read-only Python using `pathlib`, `hashlib`, `re`, `json`, and `yaml`.

Exit `0`. It recomputed registries, 17 coverage rows, 52/52 checker reference closure, 16 vectors, 18 JSON examples, and YAML parsing.

5. Conflict reproduction: inline read-only Python computed both marker-boundary hash variants and extracted same-version schema field sets.

Exit `0`. It reproduced both P1 findings recorded in the review report.

## Write Boundary

Writes were limited to the four authorized additive review outputs and minimal `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md` execution metadata. No frozen subject, task, task graph, candidate, global Project Governor, repair artifact, downstream task, or runtime behavior was modified.
