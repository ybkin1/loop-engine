# T-0083 Independent Acceptance Report (10 AC)

- **Task**: T-0083 — Loop 元治理层（真实工程实践对标 + Guard Health Check + 自举审计回路 + fail-closed + 工具链完整性门 + 端到端切片）
- **Gate**: G-T-0083-REQUIREMENTS
- **Role**: independent-reviewer（独立验收，不采信任何前置报告，全部重新执行/复核）
- **Actor**: zcode-actor-57b2630ee721
- **Session**: zcode-sess-9a0b1c2d3e4f5a6b
- **Timestamp**: 2026-07-31T19:40:41+08:00
- **Environment**: Windows 10, Python 3.12 (C:\Python312\python.exe), git branch `zcode`, HEAD `d01b53e` (v3.12.22 T-0082) + T-0083 工作树变更

## Verdict summary

| # | AC | 方法 | Verdict |
|---|----|------|---------|
| AC-01 | 调研报告覆盖真实工程角色/机制 ≥10 项 | 文件存在性 + 目录/行数 + 角色章节计数 | **PASS** |
| AC-02 | 差距分析 ≥5 项结构性差距（含证据） | 章节计数 + 证据索引指向存在性抽查 | **PASS** |
| AC-03 | Guard Health Check 实现 | CLI 实跑 + 源码通读（battery/verdict） | **PASS** |
| AC-04 | 自举审计回路脚本化 | 实跑 --quick + 脚本源码核验 | **PASS** |
| AC-05 | guard 死亡测试（拦截必须生效） | mutation 测试源码核验 + 9/9 测试实跑 | **PASS** |
| AC-06 | fail-closed 默认化 | 源码路径核验（4 处 fail-open→fail-closed） | **PASS** |
| AC-07 | 工具链完整性门 | run_quality_gates.py 源码核验 | **PASS** |
| AC-08 | S1→S6 切片脚本化 | 实跑 `--task T-0082` | **PASS** |
| AC-09 | 新机制测试验证防护生效 | rc==2 / blocked 断言计数 | **PASS** |
| AC-10 | 全量测试通过无回归 | 独立全量 pytest 实跑 | **PASS** |

**OVERALL: GO**（10/10 AC PASS，全部为独立一手验证）

---

## 逐项验证详情

### AC-01 — 调研报告覆盖真实工程角色/机制 ≥10 项 — PASS

**方法**: 目录列出 + 行数统计 + 角色章节计数（`grep "^## "`）。

**证据**:
- `.ai/evidence/T-0083/research/` 存在 4 份报告，共 1939 行：
  - `roles-research.md`（586 行）— 角色调研
  - `quality-mechanisms-research.md`（503 行）— 质量机制
  - `delivery-governance-research.md`（423 行）— 交付治理
  - `ai-agent-engineering-research.md`（427 行）— AI 工程实践
- `roles-research.md` 共 17 个 `## ` 章节，其中**独立角色章节 12 个**（§1 Software Engineer … §12 Tech Writer），另有 Executive Summary、Cross-role quality mechanisms、Synthesis、Source register 等支撑章节。12 ≥ 10。

**结论**: 角色覆盖充分，报告实体真实存在（非占位）。

### AC-02 — 差距分析 ≥5 项结构性差距（含证据）— PASS

**方法**: `grep -c "^### "` + 章节清单 + 证据索引指向文件存在性抽查（13 个路径逐个 `-e` 检查）。

**证据**:
- `loop-gap-analysis.md`（54219 字节）共 **29 个 `### ` 章节**：设计层差距 **14 项**（§2.1–§2.14：无 SLO/error-budget、无 DORA 指标、无 postmortem、gate 建议性、无 bug caps、绝对门禁非增量、无 OWNERS、DoD 未形式化、无 build-cop、无 CAB、无 AI-agent 专项设计、无证据独立性 IV&V、约束内核休眠、无判定词汇表）+ 实践层差距 **8 项**（§3.1–§3.8：guard 死亡静默 PASS、fail-open 普遍、重复实现、无自审计、测试验证执行不验证防护、无元治理、运行时死锁、MCP 能力缺口）。结构性差距 22 项 ≥ 5。
- 附 `## Appendix: evidence index (file → finding)` 表，13 个引用文件**全部存在**（T-0082 六阶段报告、loop_core/*.py、hooks/scripts/*.py、.ai/gates.yaml 等）；全文含 68 处证据引用。

**结论**: 数量与证据要求均满足。

### AC-03 — Guard Health Check 实现 — PASS

**方法**: 实跑 CLI + 通读 `loop_core/guard_health.py`（新文件，untracked）。

**实跑输出**:
```
Guards checked: 5
  ALIVE:  5
  DORMANT: 0
  BROKEN: 0
Overall: PASS
```

**源码核验**（非玩具实现）:
- `GuardHealth.battery()` 定义 8 个正/负控制（GC-001…GC-008），覆盖 5 个 guard：`gate_guard`（含 fixture 隔离的 pending/approved 门禁场景）、`content_guard`（密文负控制 + 干净内容正控制）、`bash_content_guard`（重定向写负控制 + 只读正控制）、`ledger_guard`、`path_guard`。
- 状态判定：hook rc 非 0/2 → BROKEN；负控制 0 次拦截 → DORMANT；任何控制失配 → BROKEN；`overall = FAIL if (broken>0 or dormant>0)`。
- 支持 `--json` 与报告落盘（`write_report`）。

**结论**: 实现真实、可运行、判定语义完整。

### AC-04 — 自举审计回路脚本化 — PASS

**方法**: 实跑 `tools/loop_self_audit.py --quick` + 源码通读。

**实跑输出**:
```
{
  "overall": "PASS",
  "failed": []
}
```

**源码核验**: `loop_self_audit.py`（untracked）将 T-0082 阶段 0 的**人工**审计电池脚本化：quick 模式 = validate_state + guard health；full 模式追加 compileall + pytest(core) + 安全扫描 + 静态分析；结果写 `.ai/evidence/T-0083/guard-health/self-audit.json`（该文件已存在，且 full 模式此前由 test-engineer 跑出 `{"overall": "PASS", "failed": []}`，与本次 quick 结果一致）。

**结论**: 自举审计已脚本化并可复跑。

### AC-05 — guard 死亡测试（拦截必须生效）— PASS

**方法**: mutation 测试源码核验 + `pytest tests/test_guard_health.py` 实跑。

**实跑输出**: `9 passed in 7.88s`（0 failed）。

**mutation 测试核验**（`tests/test_guard_health.py::test_mutation_removing_backslash_makes_fixture_pass`，L96-124）:
- 精确复刻 T-0082 致死缺陷类别：从 `bash_content_guard.DANGEROUS_PATTERNS[0]` 正则删掉 `\s+` 中的反斜杠。
- 断言 1：变异（死）guard 对重定向写**放行** `rc_dead == 0` —— 证明 fixture 能发现 guard 死亡（若 fixture 弱，此断言失败）。
- 断言 2：恢复后的活 guard 对同一 fixture **拦截** `rc == 2` —— 证明 fixture 有判别力。
- 另有 `test_gate_guard_fixture_isolation_pending_blocks_approved_passes`（GC-001 pending 必须 block / GC-008 approved 必须 allow）覆盖 fixture 隔离路径。

**结论**: 死亡测试真实存在且证明"变异 guard 无法拦截 → 被 fixture 捕获"。

### AC-06 — fail-closed 默认化 — PASS

**方法**: `grep -n "fail-closed\|fail_closed" hooks/scripts/loop_enforcement.py` + 关键路径源码精读 + 证据报告核验。

**源码核验**（4 处 fail-open → fail-closed，均有 `T-0083` 注释标记）:
1. **HardConstraints 异常路径**（`loop_enforcement.py` L1131-1138）：`except Exception` → `should_fail_closed(root)`（`hook_common.py` L346，默认 true，配置键 `hooks.fail_closed_on_error`）→ `return EXIT_BLOCK`，stderr 输出 "BLOCKED: HardConstraints 执行异常（fail-closed）"。约束内核损坏时写入**不再静默放行**。
2. **diff-scope**（L227-262）：git 可执行文件缺失 / `git diff` rc≠0 → `(False, "…NOT_VERIFIED")`，调用点 `if not diff_ok → EXIT_BLOCK`（was fail-open）。
3. **content_guard ruff**：FileNotFoundError / 超时 / rc≠0 无输出 → fail-closed 拒绝（was 放行）。
4. **S7-S11 阶段证据判定**（L718-720）：已存在候选的任何非 PASS 判定显式记为 gate failure（"overall=X 非 PASS（fail-closed）"）。

**证据报告**: `.ai/evidence/T-0083/guard-health/fail-closed-report.md` 记录全部 4 项修复 + 各自 smoke 验证（如 BoomConstraints 抛 RuntimeError → EXIT 2；显式 `fail_closed_on_error: false` 才回退 fail-open 并注明 DEBUG ONLY）。

**结论**: 默认 fail-closed 已落地且可配置回退仅限显式 DEBUG。

### AC-07 — 工具链完整性门 — PASS

**方法**: `grep -n "tool missing\|BLOCKED" agents/quality-engineer/scripts/run_quality_gates.py` + `run_one_check` 源码精读。

**源码核验**（L266-310）: `run_one_check` 对工具缺失三标记（stderr 含 `no module named` / `not recognized as an internal or external command` / `command not found`）→ `status=STATUS_BLOCKED, gate_blocked=True, reason="tool missing (fail-closed)"`；`subprocess.TimeoutExpired` / `FileNotFoundError` / 其他异常同样 → BLOCKED（"check timeout (fail-closed)" / "tool missing (fail-closed)"）。仅 command=None（未配置）→ UNAVAILABLE（合法不阻断）。退出码契约：0=全 PASS，2=有 BLOCKED。

**结论**: 缺失工具 → BLOCKED 逻辑存在且 fail-closed。

### AC-08 — S1→S6 切片脚本化 — PASS

**方法**: 实跑 `tools/loop_vertical_slice.py --task T-0082`。

**实跑输出**（完整 JSON）:
```
S1_requirements_gate: ok — "1 user-approved gates"
S2_task_registered:   ok — "task file exists"
S4_implementation_evidence: ok — "7 phase dirs: baseline, phase-1..phase-6"
S5_quality_evidence:  ok — "8 files in phase-3/phase-5 dirs"
S6_acceptance:        ok — "acceptance-report.md exists"
failed: []   overall: "PASS"
```

**结论**: T-0082（已完成任务）切片证据链完整，脚本按 S1→S6 门禁语义校验而非执行阶段。

### AC-09 — 新机制测试验证防护生效 — PASS

**方法**: `grep -n "rc == 2\|== 2" tests/test_guard_health.py` 计数防护语义断言。

**计数结果**（6 处防护语义断言，均验证"防护生效"而非"执行成功"）:
1. `test_content_guard_blocks_secret_write`（L130）: `assert rc == 2` — 密文写入必须被拦截
2. `test_bash_content_guard_blocks_redirect_write`（L136）: `assert rc == 2` — 重定向写必须被拦截
3. `test_mutation_removing_backslash_makes_fixture_pass`（L124）: `assert run_guard_in_process(bg, FIXTURE_REDIRECT_WRITE) == 2` — 活 guard 必须拦截（判别力）
4. `test_gate_guard_fixture_isolation_pending_blocks_approved_passes`（L91）: `assert gg.blocked == 1` — GC-001 pending 门禁必须 block
5. `test_summary_overall_fails_on_broken`（L156）: `assert gh.summary()["overall"] == "FAIL"` — BROKEN ⇒ 整体 FAIL
6. `test_summary_overall_fails_on_dormant`（L163）: `assert gh.summary()["overall"] == "FAIL"` — DORMANT ⇒ 整体 FAIL（拦截 0 次 = 死 guard）

外加 mutation 判别断言 `rc_dead == 0`（L119）证明死 guard 会被捕获。

**结论**: 测试断言的是"防护/拦截"，不是"运行不报错"。

### AC-10 — 全量测试通过无回归 — PASS

**方法**: 独立实跑 `/c/Python312/python.exe -m pytest tests/ -q --tb=short`（本次会话一手数据，非采信报告）。

**实跑输出**:
```
==== 2731 passed, 63 skipped, 16 xfailed, 37 warnings in 155.72s (0:02:35) ====
```
**0 failed / 0 error**。与前置最终回归记录（2731 passed / 0 failed）完全一致。

**前置 6 个失败项的独立复核**（`regression-results.md` 记录 6 失败 → 已修复，本人逐文件重跑确认）:
- `tests/test_code_quality.py`（含 test_loop_passes_security_scan）: **13 passed**
- `tests/test_bash_readonly.py`: **77 passed**
- `tests/test_governance_consistency.py`: **12 passed**

63 skipped / 16 xfailed 为既有预期项（非 T-0083 引入）。

---

## 诚实性说明（Caveats）

1. **工作树未提交**：所有 T-0083 交付物均为 untracked（`loop_core/guard_health.py`、`tools/loop_guard_health.py`、`tools/loop_self_audit.py`、`tools/loop_vertical_slice.py`、`tests/test_guard_health.py`、`.ai/tasks/T-0083.md`、`.ai/evidence/T-0083/`），另有对 `hooks/scripts/loop_enforcement.py`、`hooks/scripts/content_guard.py`、`agents/quality-engineer/scripts/run_quality_gates.py`、`tests/test_bash_readonly.py`、`.ai/*` 的未提交修改。本验收对象为**工作树状态**（HEAD `d01b53e` + 变更）；若按提交物验收需先 commit。这与 T-0082 验收时的 CONDITIONAL GO 情况一致，属治理流程已知模式。
2. **本次验收的 AC-10 运行**与本会话并行无冲突：完整套件在本会话独立跑完（155.72s，2731/0），与 test-engineer 最终记录一致，无需引用二手数字。
3. **已知遗留项（非 10 个 AC 范围，验收不阻断）**（源自 regression-results.md 与本人观察）：
   - T-0082 任务文件状态与 task_graph 的遗留漂移（历史遗留，非 T-0083 引入）。
   - HANDOFF.json 投影中 continuity 哈希陈旧（audit_handoff.py 提示项，不影响任何 pytest 目标）。
   - T-0083 任务文件已含 `## Status`（state sync 已修复）；无未解决的新失败。
4. **mutation 测试的边界**：仅对 `bash_content_guard` 的单条正则做变异；其他 guard 的死亡由 battery 负控制（0 拦截 → DORMANT）覆盖，属不同机制但语义等价（测试 `test_summary_overall_fails_on_dormant` 覆盖该判定）。
5. 环境为 Windows + Git Bash；`tools/*.py` 仅以 `python` 运行，无 shell 依赖，可移植性未做跨平台验证（超出 AC 范围）。

---

## 最终结论

**GO** — 10/10 AC 全部通过，全部经独立一手验证（实跑命令 + 源码精读 + 文件存在性抽查）。T-0083 交付物（调研 4 报告、差距分析 22 项结构化差距、Guard Health Check、自举审计、死亡测试、fail-closed×4、工具链完整性门、纵向切片脚本）真实、可运行、有测试保护，且全量回归 2731/0 无失败。

前置条件（非本门阻断项）：交付物尚在工作树未提交；提交与后续 `## Status` 收敛由治理流程在 gate 通过后执行。
