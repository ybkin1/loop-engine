# T-0036 F003 Fresh Rereview Commands

- Read Project Governor skill and code-review skill instructions.
- Read `AGENTS.md`, `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/task_graph.yaml`, `.ai/tasks/T-0036.md`, and the relevant gate entry in `.ai/gates.yaml`.
- Ran global `validate_state.py`; startup result was exit code `0`.
- Read F003 repair implementation report, test results, final validation manifest, protected boundary postcheck, prior fresh rereview findings, and F003 fresh rereview decision packet.
- Generated `t0036-f003-fresh-rereview-subject-freeze-manifest.v0.1.yaml`.
- Spawned fresh independent read-only reviewer with `fork_context=false`.
- First full structured adapter regression failed because the live governance projection incorrectly set `current_gate_id` to an approved non-pending gate; this projection was corrected to `current_gate_id: null` before rerun.
- Second full structured adapter regression failed because `task_graph.yaml` still projected T-0036 as `active`; candidate controlled validation requires an in-progress task and in-progress gate during execution. T-0036 was projected to `in_progress` for execution-time regression rerun.
- Third full structured adapter regression failed because task file and task graph status differed; `.ai/tasks/T-0036.md` was projected to `in_progress` to match execution-time task graph status before rerun.

Further command results are recorded in dedicated evidence files.
