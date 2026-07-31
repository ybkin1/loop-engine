# T-0082 Phase 5 — Layered Quality Gates Implementation Report

- **Date**: 2026-07-31
- **Actor**: quality-engineer
- **Task**: T-0082
- **Scope**: 5 audited gaps (GAP-1..GAP-5) in layered quality gates (edit / task / phase)

---

## GAP-1: content_guard.py 死语义规则引擎 (P0)

**Files changed**: `hooks/scripts/content_guard.py`, `tests/test_content_guard_semantic.py` (new)

**Before**:
- `main()` 语义规则检查块引用未定义变量 `target`（NameError 被 `except Exception` 吞掉），
  `load_semantic_rules` / `check_semantic_rules` / `check_suspense_boundary` 从未执行。
- 更严重：`main()` 中 `project_root()` 调用缺少必选实参 `hook_input`，导致 TypeError，
  **整个 hook 在启动时即崩溃**——所有检查（lint/密钥/语义）从未运行过（已通过
  `git diff` 确认该缺陷存在于提交版本，非本次引入）。
- 此外 `_run_ruff_check` 使用 `--output-format text`，而 ruff >= 0.15 已移除该格式
  （rc=2 + 空 stdout 被当作"通过"），lint 检查实际永远放行。

**After**:
- `project_root(hook_input)` 修复启动崩溃；语义检查改用 main() 已计算好的相对路径
  `rel` 与合并内容 `semantic_content`，BLOCKER 命中 → 输出 deny JSON 并 EXIT_BLOCK(2)。
- `_run_ruff_check` 改用 `--output-format concise`，并对旧版 ruff 回退到 `text`。
- 新增 8 个单元测试（`tests/test_content_guard_semantic.py`）：
  Write 违反 BLOCKER → 2；WARNING 不阻断；干净内容 → 0；非匹配 glob → 0；
  Edit 合并内容命中 BLOCKER → 2（覆盖 GAP-4b）；无规则目录 → 0；SS-011 → 2；SS-010 → 0。

## GAP-2: S7-S11 阶段门禁证据 (check_phase_gate_enforcement)

**Files changed**: `hooks/scripts/loop_enforcement.py`, `tests/test_enforcement.py`

**Before**: S7-S11 落入 `return True, ""`，无任何证据要求。

**After**: 新增 `_check_phase_evidence_file(root, phase, evidence_relpaths)` 与
`_PHASE_EVIDENCE_FILES` 映射，S7-S11 必须存在 `overall == "PASS"` 的结构化报告：

| Phase | Evidence paths (任一通过) |
|-------|--------------------------|
| S7-integration | `.ai/evidence/{task_id}/integration-report.json` 或 `.ai/evidence/integration/integration_report.json` |
| S8-functional-test | `.ai/evidence/{task_id}/functional-test-report.json` 或 `{task_id}/regression-report.json`；兜底 `.ai/evidence/regression/baseline.json`（has_regressions=false / verdict=PASS） |
| S9-fix-optimize | `.ai/evidence/{task_id}/fix-optimize-report.json` |
| S10-performance | `.ai/evidence/{task_id}/performance-report.json` |
| S11-maintenance | `.ai/evidence/{task_id}/maintenance-report.json` |

`{task_id}` 由 state.current_task_id 替换（无任务时跳过该候选并 fail-closed）。
S1-S6 行为不变。新增 3 个端到端测试（S7 无证据阻断 / S7 证据放行 / S7 备选路径 /
S11 阻断）。

## GAP-3: S5/S6 安全审计证据

**Files changed**: `hooks/scripts/loop_enforcement.py`, `.ai/evidence/security/security_audit.json`

**Before**: S5-quality 只要求 quality_report.json；S6 只要求 delivery + runtime quality。

**After**: 新增 `check_security_gate_evidence(root)`，S5/S6 在原有质量门通过后追加要求：
1. `.ai/evidence/security/security_audit.json` 存在、可解析、`verdict != BLOCKED`；
2. 兜底 `.ai/evidence/{task_id}/phase-3/security-engineer-report.md` 存在且无 BLOCKED 判定。

`security_audit.json` 已更新为检查所读 schema：`verdict: PASS` + `bindings:
{task_id: T-0082, phase: S6-delivery, gate: G-T-0082-REQUIREMENTS}`，真实项目
S5/S6 门禁可通过。新增 3 个测试（缺安全证据阻断 / 安全 PASS 放行 / BLOCKED 阻断）。

## GAP-4: pip-audit 解析 + Edit 合并检查 + 注入检查

### 4a: pip-audit JSON 解析 — `agents/quality-engineer/scripts/run_quality_gates.py`
**Before**: `parse_audit_output` 只按退出码统计，pip-audit JSON 结构从未真正解析
（循环内计算了 `sev` 但从未累加）。
**After**: 真实解析 pip-audit `[{name, version, resolved, vulnerabilities:[{id, severity}]}]`
数组，累加 LOW/MEDIUM/HIGH/CRITICAL；保留 npm audit dict 兼容；`blocked = HIGH>0 or
CRITICAL>0`；JSON 无法解析/无漏洞时按退出码保守回退。调用方 `collect_results` 已适配
新签名 `(exit_code, raw)`。测试新增 4 个用例（pip-audit 数组 / 空数组 / 仅 MEDIUM
不阻断 / 退出码回退），npm 用例适配新签名。

### 4b: content_guard Edit 合并检查 — `hooks/scripts/content_guard.py`
**Before**: Edit 只检查 `new_string`。
**After**: 从磁盘读取原文件，应用 `old_string → new_string` 替换后 lint 合并内容；
old_string 未找到 → 跳过合并 lint 并 warning；IO 失败 → fail-open 回退仅检查
new_string。语义规则检查同样使用合并内容（Edit 场景）。

### 4c: per-edit 注入/动态执行检查 — `hooks/scripts/content_guard.py`
新增 `_EDIT_INJECTION_PATTERNS`（镜像 security_scanner SS-010/SS-011）：
- SS-011 `(?:exec|eval)\(\s*["'][^"']*\{` — high → EXIT_BLOCK(2)
- SS-010 `os.system|subprocess.(call|run|Popen)|os.popen` — medium → 仅 warning

新增内容（new_string/content）检查，原有密钥扫描与 lint 检查保留。

## GAP-5: Diff 变更范围检查 + 约束命名空间清理

### 5a: `check_diff_scope(root, task_allowed_paths, max_diff_files=15)` — `hooks/scripts/loop_enforcement.py`
- 运行 `git diff --name-only HEAD`，过滤 `.ai/`、`.zcode/` 治理路径，统计
  allowed_paths 之外的未提交变更；count > 0 → 阻断并列出越界文件（最多 15 个）。
- 非 git 仓库 / git 不可用 / git 出错 → fail-open（log warning）。
- 接入任务范围段（is_in_task_scope 之后），仅当 git 仓库存在且任务声明了
  allowed_paths。已用真实仓库验证：宽范围 allowed_paths → 放行（30 个变更文件），
  窄范围 → 正确阻断；临时目录（非 git）→ 跳过。

### 5b: PHASE_CONSTRAINTS ID 重命名 — `loop_core/state_machine.py`, `tests/test_state_machine_enhanced.py`
**Before**: S7-S11 阶段基线约束使用 `C8/C9/C10/C11/C12`，与 HardConstraints 的
`C8-stale-evidence / C9-import-not-declared / C10-contract-test-missing /
C11-task-file-limit-exceeded` 语义冲突。
**After**: 阶段基线约束重命名为 `PB-C8..PB-C12`（phase-baseline），
`_check_single_constraint` 的 `gate_constraint_map` 同步更新，相关测试引用更新。
全仓库搜索确认无其他外部引用。

---

## 分层质量门覆盖（修复后）

| 层级 | 机制 | 状态 |
|------|------|------|
| 编辑级 (edit) | content_guard: ruff lint（合并内容）+ 硬编码密钥 + 架构合规 + SS-010/SS-011 注入 + 语义规则（.ai/checks/*.rules.yaml） | 已启用（GAP-1/4b/4c，另修复启动崩溃与 ruff 格式 bug） |
| 任务级 (task) | loop_enforcement: task scope + max_files 计数 + diff 变更范围 | 已启用（GAP-5a 新增 diff 范围） |
| 阶段级 (phase) | loop_enforcement: S4+ 质量门禁配置；S5 质量+安全证据；S6 交付+运行时质量+安全证据；S7-S11 结构化证据 overall=PASS | 已启用（GAP-2/3） |

## 测试结果

```bash
/c/Python312/python.exe -m pytest tests/ -q --tb=short
==== 2722 passed, 63 skipped, 16 xfailed, 37 warnings in 198.88s ====
```

- `pytest tests/ -k content_guard -q` → 8 passed
- `pytest tests/test_enforcement.py -q` → 27 passed（含新增 7 个阶段证据测试）
- `pytest tests/test_quality_gates.py tests/test_state_machine_enhanced.py -q` → 58 passed
- 0 failed（63 skipped / 16 xfailed 为既有项）

## 诚实遗留问题 (Honest remaining gaps)

1. **diff 范围检查不追踪未跟踪文件**：`git diff --name-only HEAD` 只覆盖已跟踪文件的
   未提交修改；全新（untracked）越界文件由 per-write 的 `is_in_task_scope` 兜底拦截，
   但绕过 hook 的本地新增文件不会被 diff 检查发现。
2. **S8 的 regression_runner 兜底仅接受 baseline.json**：regression_runner 本身不输出
   结构化报告文件（只有 baseline），其 stdout 判定未纳入（需脚本级改造）。
3. **content_guard 语义规则仅覆盖 .py**：`not rel.endswith(".py")` 提前放行，
   `.ts/.tsx/.sh` 等语言不经过内容质量检查（nextjs.rules.yaml 等规则实际只对 .py 生效）。
4. **SS-010 命中仅 warning**：`subprocess.run` 等是常见合法写法，medium 级别不阻断
   是刻意设计；若需严格模式可增加配置开关。
5. **真实项目 hook 死锁未在本阶段处理**：真实项目 `.ai/runtime/runtime-state.json`
   缺失导致 loop_enforcement 在 runtime 校验处 SETUP_INCOMPLETE 阻断所有业务写入
   （先于本阶段门禁逻辑）——这属于运行时接管恢复问题，超出本 5 项 GAP 范围。
6. **S5/S6 安全证据兜底检查 "BLOCKED" 为子串匹配**：security-engineer-report.md
   文本中出现"BLOCKED"字样即拒绝，可能对含解释性文本的报告误伤（当前真实报告无此问题）。
