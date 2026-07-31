# T-0082 Phase 4: Unified Side-Effect Authorization — Security Engineer Report

- **task_id**: T-0082
- **phase**: S4-implementation (Phase 4 security-engineer — side-effect authorization)
- **role**: security-engineer
- **timestamp**: 2026-07-31
- **scope**: hooks/scripts/, hooks/hooks.json, loop_core/runtime_controller.py, tests/

## Summary

Closed four audit findings from the Phase 4 authorization audit: a 100% dead
`bash_content_guard.py` (corrupted regexes + crash on import + crash in
`main()`), a readonly-classification bypass for side-effect-capable commands
(python/node/npx/7z/powershell/…), an inconsistent main-thread write denial
message, and the Node REPL (`mcp__node_repl__js`) PreToolUse matcher gap.
All fixes verified with unit and subprocess-level tests.

---

## 1. Channel coverage table (before / after)

| Channel | Before | After | Mechanism |
|---|---|---|---|
| Write / Edit / ApplyPatch | gated | gated | content_guard, gate_guard, loop_enforcement (unchanged) |
| Bash `echo/cat >` redirects | **dead** (corrupted regex) | BLOCKED | bash_content_guard pattern 1 (+11 heredoc) |
| Bash `cp/mv/rm/touch` | **dead** | BLOCKED | bash_content_guard pattern 2 |
| Bash `dd` | **dead** | BLOCKED | bash_content_guard pattern 3 |
| Bash `curl/wget -o` | **dead** | BLOCKED (in-project targets) | bash_content_guard pattern 4 |
| Bash `git checkout --/reset --hard/clean` | **dead** | BLOCKED | bash_content_guard pattern 5 |
| Bash `tee` | **dead** | BLOCKED | bash_content_guard pattern 6 |
| Bash `sed -i` | **dead** | BLOCKED | bash_content_guard pattern 7 |
| Bash python/node inline writes | **dead** | BLOCKED | bash_content_guard pattern 8 |
| PowerShell `Set-Content/Out-File/Add-Content` | **dead** | BLOCKED | bash_content_guard pattern 9 |
| Archive extraction `tar -x/unzip/7z x` | **dead** | BLOCKED | bash_content_guard pattern 10 |
| `python script.py` / `python -m X` | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` in `is_readonly_command` |
| `node -e` / `node script.js` | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` |
| `npx` generators | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` |
| `7z x`, `xz -d`, `gzip`, `zstd`, `rar x` | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` |
| `powershell`/`pwsh` | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` |
| `copy`/`del`/`move`/`ren` (cmd) | **readonly (bypass)** | NOT readonly | `_SIDE_EFFECT_CAPABLE` |
| `mcp__node_repl__js` (Node REPL) | **no hook coverage (bypass)** | gated (fail-closed) | hooks.json matcher + loop_enforcement `mcp__` branch |
| Main-thread business write | `MAIN_THREAD_BUSINESS_WRITE_DENIED` | `MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN` | runtime_controller.authorize_write |

---

## 2. bash_content_guard.py repair

File: `hooks/scripts/bash_content_guard.py`

Repair evidence:
- 20 lines contained literal 0x08 backspace bytes where `\b` belonged (33
  bytes counted across the file via `grep -c $'\x08'`).
- Every `\s`/`\S`/`\d` had lost its backslash (e.g. `s*S+`).
- The python-inline pattern had an unbalanced `(` → `re.error` at import time
  → the module crashed on EVERY PreToolUse invocation (exit 1 before any
  check ran).
- Additionally `main()` called `project_root()` without the required
  `hook_input` argument → `TypeError` on every invocation, so even a fixed
  import would still crash.

Fixes:
- Rewrote `DANGEROUS_PATTERNS` from the intended 10-pattern list, each
  verified with `re.compile` at import time (`ALL_PATTERNS_COMPILE` verified
  separately). Kept the original heredoc pattern (`<<\w+ ... >>?`) as an 11th
  entry — it also covers `python - <<EOF > file`, which the 10 mission
  patterns do not.
- Fixed `SAFE_COMMAND_PATTERNS` and `_extract_target_path()` regex escapes
  (same corruption).
- Fixed `project_root(hook_input)` call.
- Fixed `_is_in_project()`: it resolved relative targets against the hook
  process CWD instead of the project root, so a relative target like
  `test.py` was treated as "outside the project" whenever the hook ran with a
  different CWD (this is why the pre-existing `TestBashContentGuard` tests
  only "passed" via the crash exit code 1). Now resolves relative targets
  against `project_root`.

Behavior verified (subprocess-level, temp governed project):
- `echo "bad" > test.py` → exit 2 (deny)
- `cp source.py dest.py` → exit 2
- `python -c "open('x','w')"` → exit 2
- `git checkout -- src/a.py` → exit 2
- `7z x archive.zip`, `tar -xzf a.tar`, `unzip a.zip` → exit 2
- `sed -i`, `tee`, `dd of=`, `powershell Set-Content` → exit 2
- `ls -la`, `cat file.txt`, `python --version` → exit 0
- `curl -o /tmp/out …` (absolute target outside project) → exit 0 by design
  (outside-project writes are delegated to path guards)

---

## 3. _hook_bash.py readonly expansion

File: `hooks/scripts/_hook_bash.py`

- Added `_SIDE_EFFECT_CAPABLE` (python, python3, node, npx, 7z, xz, gzip,
  zstd, rar, powershell, pwsh, copy, del, move, ren) and `_SAFE_SCRIPTS`
  (`--version`, `-V`, `help`, `--help`, `-h`, `-c "print`, `-c 'print`).
  These commands were deliberately NOT added to `_WRITE_CMDS` (that would
  make `python --version` classify as a write).
- `is_readonly_command()` now returns False when the first command token is a
  `_SIDE_EFFECT_CAPABLE` name (or a versioned interpreter matching
  `python[23]?(?:\.\d+)?`) UNLESS a `_SAFE_SCRIPTS` marker is present — in
  which case it returns True (readonly). The check sits before the legacy
  `-c` blanket rule so `python -c "print(1)"` stays readonly while
  `python -c "import os; os.system(...)"` is not.
- Shell-write operators (`>`, `>>`, `2>`, `| tee`, `find -delete`, etc.) are
  still caught first by `has_write_operations`.

Mission verification matrix: 14/14 OK, 0 FAILS (including `python --version`
→ True, `python -m pytest tests/` → False, `python script.py` → False,
`node -e fs.writeFileSync` → False, `7z x archive.zip` → False,
`powershell Set-Content x` → False, `tar -xzf a.tar` → False, `git log` →
True, `ls -la` → True).

---

## 4. MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN unification

- `loop_core/runtime_controller.py` `authorize_write()`: reason string
  changed from `MAIN_THREAD_BUSINESS_WRITE_DENIED` to
  `MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN` (T-0082 requirement).
- `tests/test_runtime_controller.py:56` updated to assert the new string.
- Verified with an approved-execution simulation:
  `allowed=False reason=MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN` →
  `MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN_OK`.

Note: the mission's simulation snippet, run verbatim against the live
project, returns `NO_ACTIVE_TASK_OR_PROPOSAL` instead — the live project's
runtime snapshot is not in an approved-execution state, and that check
precedes the main-thread check in `authorize_write()`. The FORBIDDEN branch
requires an active approved execution, which the temp-project simulation
provides.

---

## 5. hooks.json matcher + loop_enforcement.py mcp__ gate

- `hooks/hooks.json` PreToolUse matcher extended from
  `Read|Write|Edit|Bash|ApplyPatch|Agent|Skill` to
  `Read|Write|Edit|Bash|ApplyPatch|Agent|Skill|mcp__node_repl__js|Notebook|Task`.
  **This takes effect on the next ZCode session restart — it is registered by
  the CLI from hooks.json at session start and is NOT hot-reloaded.**
- `hooks/scripts/loop_enforcement.py`: added the T-0082 Phase 4 `mcp__`
  branch BEFORE the `is_orchestration` early-pass so MCP tools never get the
  orchestration bypass:
  - `tool_name.startswith("mcp__")` and no active task → `EXIT_BLOCK`
    (fail-closed: `DISPATCH_REQUIRED`).
  - Extended the runtime-projection identity gate so `mcp__` tools also
    require `actor_id` + `caller_class` in runtime-managed projects
    (previously identity was only checked for `business_tools`).

End-to-end simulation (subprocess, temp FULL-mode project):
- `mcp__node_repl__js`, no task → exit 2 (BLOCK)
- `mcp__node_repl__js`, task T-1, no identity → exit 2 (BLOCK)
- `loop_mode: LIGHTWEIGHT` → exit 0 (PASS, guard off)

Operational consequence (documented honestly): in FULL/STANDARD mode an MCP
tool with an active task and identity still ends blocked at the final static
task-scope check, because its target cannot be statically extracted
(`is_in_task_scope(None, …)` is always False). This is the fail-closed
interpretation of "same gate as Bash without a target": un-scopeable side
effects are denied. After the restart, `mcp__node_repl__js` will therefore be
unusable inside governed FULL-mode projects unless a future capability model
gives it a scoped identity + target — see remaining gaps.

---

## 6. Verification results

- `tests/test_runtime_controller.py tests/test_hooks.py tests/test_enforcement.py`
  → 41 passed (all).
- `tests/test_bash_readonly.py tests/test_bypass_matrix.py tests/test_deep_qa_probe.py`
  → 324 passed, 15 xfailed (after updating 18 stale expectations, see §7).
- `tests/test_hook_guards.py tests/test_role_isolation.py tests/test_cross_layer_safety.py
  tests/test_governance_consistency.py tests/test_hook_integration.py
  tests/test_gate_guard_lifecycle.py tests/test_ledger_guard.py` → 127 passed
  (incl. the 3 TestBashContentGuard subprocess tests, which previously only
  "passed" because the script crashed with exit 1).
- Combined sweep of all affected suites: 572 passed, 16 xfailed, 0 failed.
- Readonly classification matrix: 14/14 OK (0 FAILS).
- `MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN` simulation: OK.
- `import bash_content_guard` → IMPORT_OK; `py_compile` of all modified files
  → COMPILE_OK; hooks.json parses and contains the new matcher terms.

---

## 7. Test expectations updated (stale assertions)

18 tests asserted the OLD (bypass) classification and were updated because
the new behavior is the explicitly required Phase 4 policy:

- `tests/test_bash_readonly.py`: test_pytest_simple, test_pytest_with_python3,
  test_flake8, test_mypy, test_ruff_check, test_python_script, test_node_script,
  test_python_build_check — flipped `assertTrue` → `assertFalse` with
  T-0082 docstrings.
- `tests/test_bypass_matrix.py`: test_pytest_readonly, test_unittest_readonly,
  test_flake8_readonly, test_mypy_readonly, test_ruff_check_readonly,
  test_pylint_readonly, test_bandit_readonly, test_build_check_readonly,
  test_python_script_readonly, test_node_script_readonly — flipped to
  `assertFalse`; class docstring updated to describe the new policy.

Bare `pytest tests/`, `nosetests`, `tox`, `pylint` (no python prefix),
`black --check`, `isort --check`, `pip list`, `npm list/audit`, `git status`,
`ls` etc. remain readonly — unchanged.

---

## 8. Remaining gaps (honest assessment)

1. **Matcher changes need a restart.** hooks.json is read by the CLI at
   session start; the extended matcher (mcp__node_repl__js, Notebook, Task)
   and all edited hook scripts take effect only after the next ZCode session
   restart. The `auto_sync_to_plugin_cache` self-heal copies local
   hooks/scripts/*.py and hooks/*.json into the plugin cache on the next hook
   invocation, but the new matcher is only honored after restart. No
   hot-reload was attempted, per instruction.
2. **`python -c "print(...)"` is classified readonly by design** (safe-marker
   rule), so `python -c "print(open('/tmp/x','w'))"`-style obfuscation that
   embeds the literal prefix `print` after `-c` is not flagged by the
   readonly classifier. bash_content_guard still blocks `python …open(`,
   and loop_enforcement's task-scope gate still applies; this is a residual
   heuristic gap of the documented safe-marker trade-off.
3. **`curl … | bash` remains classified readonly** (pipe-to-shell execution,
   pre-existing classification asserted by tests/test_deep_qa_probe.py:315 as
   an xfail-known-limitation). Not part of the Phase 4 mandated list; noted
   for a future phase.
4. **MCP tools have no statically extractable target**, so in FULL/STANDARD
   mode they are fail-closed blocked even with identity + active task. If
   Node REPL (or other MCP side-effect tools) must be usable inside governed
   projects, a capability model (explicit MCP tool allow-list in the task
   contract, or a runtime capability with a scoped sandbox) is the required
   follow-up; the current gate intentionally errs on the side of blocking.
5. **bash_content_guard heuristic limits**: patterns like `grep -o` after a
   `curl` in the same command can produce conservative false positives
   (blocked); targets outside the project root are deliberately delegated to
   path guards rather than blocked here.
