# Failure Recovery Steps v0.1

Task: T-0014

## If A Pending Gate Already Exists

1. Stop immediately.
2. Report the pending gate ID.
3. Ask the user to approve, reject, or request repair.
4. Do not create or modify T-0014 content.

This did not occur at startup; validation returned `[ok] state is usable`.

## If AGENTS.md Changes During T-0014

1. Stop immediately.
2. Capture current `AGENTS.md` hash and last-write time.
3. Compare against baseline:

```text
DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87
```

4. Do not continue gate preparation until the user decides whether to repair or discard the package.

## If Proposed Diff Does Not Apply In Future

1. Do not edit `AGENTS.md` manually to approximate the patch.
2. Capture the patch failure and current target hash.
3. Mark the execution task blocked.
4. Request repair of the package.

## If Future Startup Verification Fails

1. Stop governed work.
2. Capture the failing scenario and evidence.
3. Restore or reverse the `AGENTS.md` change under the approved recovery scope.
4. Rerun `validate_state.py`.
5. Record recovery evidence.
6. Keep the repaired method not installed until a corrected package is approved.

## If Validation Output Is Unexpected

1. Do not reinterpret validator success or failure as approval.
2. Record exact command and output.
3. Inspect `.ai/state.yaml`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Ask the user for a repair decision if the state cannot be safely reconciled inside the current scope.
