# Commands For T-0037

## Execution authorization

- User request: `执行 G-T-0037-CODEX-LOOP-CANDIDATE-IMPLEMENTATION-V0-1`
- Gate execution status: `in_progress` during implementation; candidate completion is recorded after validation.
- Scope remained limited to `codex_loop/`, `tests/codex_loop/`, `docs/codex-loop/`, and T-0037 evidence/state files.

## Unit test commands

Each command was run with `runpy` because `tests/codex_loop` shadows the normal unittest discovery package name:

```text
python -c "import runpy; runpy.run_path('tests/codex_loop/test_role_registry.py', run_name='__main__')"
python -c "import runpy; runpy.run_path('tests/codex_loop/test_context_isolation.py', run_name='__main__')"
python -c "import runpy; runpy.run_path('tests/codex_loop/test_planning.py', run_name='__main__')"
python -c "import runpy; runpy.run_path('tests/codex_loop/test_packets_and_checks.py', run_name='__main__')"
python -c "import runpy; runpy.run_path('tests/codex_loop/test_cli_and_materials.py', run_name='__main__')"
python -c "import runpy; runpy.run_path('tests/codex_loop/test_runtime.py', run_name='__main__')"
```

Result: all six test files passed; total tests: 28.

## T-0036 local candidate exercise

Fixture: `.ai/evidence/T-0037/fixture/t0036/`

```text
roles-validate -> PASS; 12 role contracts and bounded prompt markers
init -> initialized Codex project store
phases -> wrote P0-P12 phase snapshot
plan -> wrote role-per-phase dependency graph
select-materials -> candidate; selected ARCH-002 and ARCH-003
demo-t0036 -> wrote Functional Design Packet and P11 Human Review Packet
prepare-run -> READY_TO_INVOKE; research-engineer run envelope and invocation spec written
verify -> PASS; role_registry, role_prompts, candidate_store
```

The prepared run explicitly records `capability_probe.status=NOT_RUN` and `execution_status=not_performed_by_candidate`.

## Governance validation

```text
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
git diff --check
```

Both passed at the implementation checkpoint. Final handoff audit is recorded separately during closeout.

## Static boundary review

- No network, subprocess, socket, or external host adapter imports were found in the candidate runtime.
- Secret scans found only the deliberate marker list and its negative test input; no secret value was added.
- `git diff --check` passed.
