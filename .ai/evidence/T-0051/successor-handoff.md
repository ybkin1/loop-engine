# T-0051 successor handoff brief

## Handoff objective

Continue P0 architecture repair from the residual findings recorded in `.ai/HANDOFF.md`.

## Confirmed not fixed

- PreToolUse matcher excludes `Read`; main-thread Read is not governed.
- Read-only Bash is explicitly passed by `loop_enforcement.py`; project exploration through `find`, `grep`, `ls`, and `git status` is not blocked when no task exists.
- Main-thread business-write blocking exists, but main-thread orchestration-only behavior is not complete.
- RuntimeController is conditional on `.ai/runtime/runtime-state.json`; legacy and canonical policies coexist.
- Bootstrap/Proposal/Recovery ordering has not been proven in no-task state.
- Fail-closed behavior lacks a safe, restricted recovery path and may self-lock main and child agents.

## Required next outcome

Implement one policy kernel for Read/Write/Edit/ApplyPatch/Bash/MCP/Executor/Agent. Distinguish minimal metadata read, Bootstrap, Proposal, Governance Recovery, project exploration, and business writes. Preserve a recovery path that cannot write business code, approve gates, activate tasks, or issue capabilities.

## Mandatory proof

Run negative tests for no-task Read, no-task exploration, Bootstrap, Proposal, corrupted runtime state, recovery restrictions, stale Hook cache, main-thread capability misuse, reviewer identity reuse, and cross-entry policy consistency. Report targeted, non-lab, legacy lab, and real-host live-fire results separately.

## Safety rule

Do not claim P0 closed from passing tests. `validate_state`, reviewer PASS, and validator output are evidence only. Do not modify AGENTS.md or enter real business projects.
