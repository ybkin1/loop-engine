# T-0036 Fresh Independent Rereview Commands

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-ALL-FINDINGS-V0-1`

All commands used explicit candidate paths and `PYTHONDONTWRITEBYTECODE=1`, with no global candidate activation or live structured-state writes.

```text
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
C:\Python312\python.exe -B candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py -v
C:\Python312\python.exe -B candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py T0036RepairRedContractTests.test_E2E_CURRENT_001_contract_entrypoint_exists -v
C:\Python312\python.exe -B candidates/T-0030-project-governor-repair/scripts/governance_action.py C:\Users\Administrator\.codex\loop-engine-lab capability
C:\Python312\python.exe -B candidates/T-0030-project-governor-repair/scripts/validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
```

Additional temporary fixture probes were executed under the system temporary directory and cleaned by fixture teardown:

```text
controlled runner with a zero-test command printing `Ran 1 test in 0.001s` and `OK`
```

No candidate, protected subject, live `.ai/project_continuity.yaml`, live `.ai/transaction_registry.yaml`, or governance projection was modified.
