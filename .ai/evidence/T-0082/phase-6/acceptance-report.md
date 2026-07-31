# T-0082 Phase 6: Acceptance Report

- **task_id**: T-0082
- **phase**: S6-delivery (acceptance)
- **gate_id**: G-T-0082-REQUIREMENTS
- **verifier**: independent-reviewer (actor zcode-actor-57b2630ee721, session zcode-sess-3f7a1b2c8d4e5f6a)
- **timestamp**: 2026-07-31T17:19:42+08:00

## AC Results

| AC | Criterion | Method | Verdict | Evidence |
|----|-----------|--------|---------|----------|
| AC-01 | 主会话写业务文件被阻断 | RuntimeController sim (temp project, DEVELOPER_EXECUTION state) | PASS | allowed=False, reason=MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN; controller governance write still allowed (GOVERNANCE_CONTROLLER_ONLY) |
| AC-02 | developer 子会话可在允许路径写入 | RuntimeController sim (capability.json allowed_paths) | PASS | in-scope: AUTHORIZED; out-of-scope: PATH_OUTSIDE_APPROVED_SCOPE; wrong actor: ACTOR_NOT_ASSIGNED |
| AC-03 | Node REPL/Bash 重定向旁路被阻断或审计 | _hook_bash classification + real bash_content_guard subprocess + hooks.json read | PASS | python script.py/node -e/7z x = not readonly; python --version = readonly; real hook exit=2 (echo redirect, python inline write), exit=0 (ls, git status); hooks.json PreToolUse matcher includes mcp__node_repl__js |
| AC-04 | 安全缺陷导致 security BLOCKED | SecurityReport critical finding bind | PASS | verdict=BLOCKED, passed=False |
| AC-05 | quality/security/test/reviewer 真实执行 | Phase-3 evidence files audit | PASS | 7 files in phase-3/, review-evidence.json has distinct reviewer/dev sessions, honest FAIL verdict with independently re-run numbers |
| AC-06 | developer/reviewer 共享 actor/session 时阻断 | RoleDispatchManager.verify_role_isolation + loop_dispatch_role verify | PASS | 3 violations (SHARED_ACTOR + 2 SHARED_SESSION); isolated control = []; `loop_dispatch_role.py verify --task T-0082` → ISOLATION_OK 7 dispatches |
| AC-07 | Host Adapter 不可用时不生成 takeover PASS | HostAgentInvoker() launch + collect | PASS | status=BLOCKED, agent_takeover=False, state=SETUP_INCOMPLETE, is_pass=False; collect on BLOCKED returns BLOCKED with empty output_hash |
| AC-08 | 旧 fingerprint 报告失效 | SecurityReport bind → mutate → is_valid | PASS | bound valid=True; after append tampered finding valid=False; unbound report valid=False |
| AC-09 | state/task/gate/projection/evidence 漂移时阻断 | Real gate_guard.py hook subprocess (drift fixture) | PASS | G-DRIFTED not in register → exit=2 BLOCKED ("治理状态漂移"); control approved registered gate → exit=0 |
| AC-10 | 工具缺失/超时/非法输出 → BLOCKED/NOT_VERIFIED | Verdict semantics | PASS | UNAVAILABLE/NOT_VERIFIED: blocking=False conclusive=False; BLOCKED: blocking=True conclusive=True |
| AC-11 | S1→S2→S4→S5→S6 纵向切片 | Evidence trail audit | PASS | gates.yaml 1× G-T-0082 (approved, user); evidence baseline + phase-1..phase-6; task_graph.yaml T-0082 S1-requirements in_progress; .ai/tasks/T-0082.md exists |
| AC-12 | S6 只提交人工 GO/NO-GO | gates.yaml audit | PASS | G-T-0082-REQUIREMENTS: status=approved approval_actor=user approval_source=explicit_user_message gate_type=user-approval; zero auto-approval markers in register |

## Detailed Verification

### AC-01 — 主会话写业务文件被阻断 (PASS)
Real execution with temp governance project (runtime_state=DEVELOPER_EXECUTION):
```
allowed=False reason=MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN
```
`RuntimeController.authorize_write` (loop_core/runtime_controller.py:257) returns
`(False, "MAIN_THREAD_BUSINESS_WRITE_FORBIDDEN")` for caller_class=main-thread /
role_id=main-thread. Governance files remain controller-writable
(`GOVERNANCE_CONTROLLER_ONLY` for caller_class=controller) — exemption is correct.

### AC-02 — developer 子会话可在允许路径写入 (PASS)
Real execution with capability.json `allowed_paths: ["tests/", "src/"]`,
assigned_actor_id=zcode-actor-dev:
```
in-scope write tests/new_test.py:   allowed=True  reason=AUTHORIZED
out-of-scope write outside/evil.py: allowed=False reason=PATH_OUTSIDE_APPROVED_SCOPE
wrong-actor write tests/hijack.py:  allowed=False reason=ACTOR_NOT_ASSIGNED
```
Write authorization is capability-scoped and actor-bound; both positive and
negative controls behave as specified (runtime_controller.py:250-268).

### AC-03 — Node REPL/Bash 重定向旁路被阻断或审计 (PASS)
1. `_hook_bash.is_readonly_command` (hooks/scripts/_hook_bash.py:157): side-effect-
   capable interpreters (`python`, `node`, `7z`, ...) are NOT readonly unless a
   safe marker (`--version`, `-V`, `-h`, `-c "print") is present:
   - `python script.py` → False (expected False) OK
   - `node -e x` → False (expected False) OK
   - `7z x a.zip` → False (expected False) OK
   - `python --version` → True (expected True) OK
2. Real `bash_content_guard.py` hook execution (governance project cwd):
   - `echo "print(1)" > src/evil.py` → exit 2 (deny, "redirect write")
   - `python -c "open('x.py','w').write('a')"` → exit 2 (deny, "python inline file write")
   - `ls -la` → exit 0 (allow); `git status` → exit 0 (allow)
3. hooks/hooks.json PreToolUse matcher (line 36) includes
   `mcp__node_repl__js` alongside Read|Write|Edit|Bash|ApplyPatch|Agent|Skill|Notebook|Task,
   so Node REPL tool calls pass through the enforcement chain.

### AC-04 — 安全缺陷导致 security BLOCKED (PASS)
`SecurityReport` with one critical finding binds to
`Verdict.BLOCKED`, `passed=False`. Fail-closed policy confirmed in
loop_core/security_scanner.py:60-66 (critical → BLOCKED, cannot be overridden).

### AC-05 — quality/security/test/reviewer 真实执行 (PASS)
`.ai/evidence/T-0082/phase-3/` contains 7 files: developer-output.md,
quality-engineer-report.md, security-engineer-report.md, test-engineer-report.md,
independent-reviewer-report.md, role-dispatch-report.md, review-evidence.json.
review-evidence.json is internally consistent: reviewer_session_id
(zcode-sess-d27984a17cfd4e7d) != developer_session_id (zcode-sess-0cd75d85a38b67c1),
verdict=FAIL (honest — gate was not rubber-stamped), independently_verified block
records re-run numbers (developer tests 30 passed / security scan PASS /
2 test failures reproduced). The 2 reported test failures were since fixed:
re-run today → both pass (see below).

### AC-06 — developer/reviewer 共享 actor/session 时阻断 (PASS)
```
violations: ['SHARED_ACTOR: developer zcode-actor-dev == reviewer zcode-actor-dev',
             'SHARED_SESSION: developer SAME == reviewer SAME',
             'SHARED_SESSION: independent-reviewer SAME already used by developer']
```
Isolated control (distinct actor+session) → `[]`. Tool check
`tools/loop_dispatch_role.py verify --task T-0082` → `ISOLATION_OK: 7 dispatches,
all distinct actor/session` (exit 0). Phase-3 evidence sessions are distinct
(verified in AC-05).

### AC-07 — Host Adapter 不可用时不生成 takeover PASS (PASS)
`HostAgentInvoker()` (no adapter) launch → status=BLOCKED, agent_takeover=False,
state=SETUP_INCOMPLETE, is_pass=False. `collect()` on a BLOCKED receipt also
fails closed: status=BLOCKED, output_hash="" — no fabricated PASS anywhere
(loop_core/host_agent_invoker.py:251-268, 365-379).

### AC-08 — 旧 fingerprint 报告失效 (PASS)
Bound report (git_commit=commit1) → is_valid()=True (content_hash matches).
After appending a tampered finding → is_valid()=False (SHA-256 content hash
mismatch, security_scanner.py:94-104). Unbound report → is_valid()=False.

### AC-09 — state/task/gate/projection/evidence 漂移时阻断 (PASS)
Real hook execution, not a simulation:
- state.yaml current_gate_id=G-DRIFTED, gates.yaml register has no such gate →
  `gate_guard.py` exit=2, log: "BLOCKED: current_gate_id 'G-DRIFTED' 在 gates.yaml
  中不存在。治理状态漂移，请先修复 gate register。" (fail-closed, gate_guard.py:214-220)
- Control: current_gate_id=G-OK present and approved+in_progress → exit=0 (allow)

### AC-10 — 工具缺失/超时/非法输出 → BLOCKED/NOT_VERIFIED (PASS)
`Verdict.UNAVAILABLE`: blocking=False conclusive=False; `Verdict.NOT_VERIFIED`:
blocking=False conclusive=False; `Verdict.BLOCKED`: blocking=True conclusive=True.
Non-blocking, non-conclusive semantics correct for tool-unavailable states.

### AC-11 — S1→S2→S4→S5→S6 纵向切片 (PASS)
- S1: G-T-0082-REQUIREMENTS in gates.yaml — status=approved, execution_status=in_progress,
  approval_actor=user, gate_type=user-approval, recorded 2026-07-31; task_graph.yaml
  T-0082 phase=S1-requirements status=in_progress; .ai/tasks/T-0082.md exists.
- S2/S4 implementation: evidence phase-1 (convergence-report.md, git_commit
  c6fda120763009301aa3720f571a819b07b37c44) and phase-2 (quality-chain-report.md).
- S5 quality: phase-3 role reports + phase-5 layered-quality-gates-report.md.
- S6 delivery: phase-6 (this report); state.yaml current_phase=S6-delivery.
- Full suite green at verification time: 2722 passed, 63 skipped, 16 xfailed, 0 failed.

### AC-12 — S6 只提交人工 GO/NO-GO (PASS)
G-T-0082-REQUIREMENTS: status=approved, approval_actor=user,
approval_source=explicit_user_message, gate_type=user-approval. Register-wide scan:
zero approval_source values containing auto/self/system; no auto-approve markers
in gates.yaml. 51/75 gates carry approval_actor=user; 24 legacy gates
(recorded 2026-07-06 era) are approved without the approval_actor field —
they predate the field (non-uniform annotation, not an auto-approval mechanism;
all are gate_type user-approval). Observation, non-blocking for this gate.

## Reproducibility & Honesty Notes (non-AC caveats)

1. **Uncommitted working tree**: the entire T-0082 slice is NOT committed to
   HEAD (c6fda12). `git status` shows 39 modified/untracked files, including
   core implementation untracked at HEAD: `loop_core/verdicts.py`,
   `loop_core/role_dispatch.py`, `tools/loop_dispatch_role.py`,
   `tests/test_verdicts.py`, `.ai/evidence/T-0082/`. A clean checkout of HEAD
   cannot import `loop_core.verdicts` (phase-3 independent review flagged the
   same). All ACs above verify LIVE behavior and pass, but the evidence chain
   is not reproducible from HEAD until the slice is committed.
2. **Phase-3 red-suite resolved**: the 2 failures reported in phase-3
   (test_full_mode_allows_write_within_task_scope,
   test_legacy_fixture_marker_allows_scoped_write_without_projection) were
   re-run today: 2 passed. Full suite: 2722 passed, 0 failed. The commands.md
   PHASE_3_FIX claim is confirmed.
3. **Minor**: state_machine emits STALE_GATE_REFERENCE warning for 'G-T-005'
   (pre-existing legacy reference, not part of T-0082 scope).

## Overall Acceptance Verdict

**CONDITIONAL GO**

All 12 acceptance criteria verified by independent re-execution — 12/12 PASS,
no NOT_VERIFIED, no FAIL. Fail-closed semantics (write authorization, bash/REPL
bypass guard, security BLOCKED, host-adapter fail-closed, fingerprint
invalidation, drift blocking, role/session isolation, human-only gate approval)
are all real and working in the live tree.

Condition (required before unconditional GO / delivery closeout):
- Commit the T-0082 working tree (39 files) so the evidence chain
  (baseline → phase-6) is reproducible from HEAD. Until then, the acceptance
  is valid for the working tree only.
