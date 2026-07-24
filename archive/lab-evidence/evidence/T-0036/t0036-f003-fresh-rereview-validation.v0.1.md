# T-0036 F003 Fresh Rereview Validation

Validation before final closeout projection:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable
```

Final validation after rereview completion:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable
LASTEXITCODE=0
```

Cache/compiled artifact postcheck under `candidates/T-0030-project-governor-repair` found no `__pycache__`, `.pyc`, or `.pyo` entries.

Post-compaction independent rereview correction:

```text
focused RUN_002-RUN_009: 8/8 OK, LASTEXITCODE=0
full structured adapter regression from completed current disk state: 63/64, LASTEXITCODE=1
failure: AUTHORITY_MISSING: Controlled validation requires one Gate-bound in-progress execution
cache/compiled artifact postcheck: none
```

Because the full regression is not reproducible from the completed current disk state, the final evidence-only rereview verdict is `REPAIR_REQUIRED`.

Final validator after `REPAIR_REQUIRED` governance projection:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable
LASTEXITCODE=0
```
