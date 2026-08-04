# T-0114 执行命令日志（developer 子代理段：B 组 4 死工具删除）

日期：2026-08-03
任务卡：`.ai/tasks/T-0114.md`（用户 gate 批准的 B 组 4 文件删除）
复核依据：`.ai/evidence/T-0111/fixes/final-audit.md`（B 组定性：tool_task_queue 死壳 /
tool_eval / loop_vertical_slice / loop_dispatch_role 0 调用方独立 CLI）
基线提交：6e030e6（v3.12.49，回滚点）

## 已执行命令（可复现）

```bash
# ── 0. 基线：删除前 git HEAD 确认 ────────────────────────────────────
git log --oneline -1        # 6e030e6 v3.12.49（回滚提交点）
git status --short          # 确认预存改动（.ai/HANDOFF.md 等主会话改动，本任务不动）

# ── 1. 引用面确认（删除前 grep，零隐式依赖）─────────────────────────
grep -rn -E "tool_task_queue|tool_eval|loop_vertical_slice|loop_dispatch_role" \
  --include="*.py" . | grep -v __pycache__ | grep -v .ai/evidence
#   仅剩 capability_registry manifest 4 条目 + 4 个文件自身 docstring
grep -rn -E "tool_task_queue|tool_eval|loop_vertical_slice|loop_dispatch_role" tools/server.py
#   server.py TOOLS/_dispatch 零引用（4 工具 MCP 未注册，T-0111 定性一致）
grep -rn -E "tool_task_queue|tool_eval|loop_vertical_slice|loop_dispatch_role" tests/ docs/ .ai/README.md
#   tests/docs/.ai/README 零引用（deep_probe_v35 TOOL_MODULES 亦不含）

# ── 2. 删除 4 个文件（精确清单，git rm 原子暂存）────────────────────
git rm tools/tool_task_queue.py tools/tool_eval.py \
        tools/loop_vertical_slice.py tools/loop_dispatch_role.py
git diff --cached --diff-filter=D --name-only
#   恰 4 项 D：tool_task_queue / tool_eval / loop_vertical_slice / loop_dispatch_role（AC-01）

# ── 3. 引用同步写路径（allowed_paths 内）────────────────────────────
# loop_core/capability_registry.py：manifest 删 4 条目 + 头注释 30→26
#   （loop_dispatch_role / loop_vertical_slice / tool_eval / tool_task_queue）
# tools/server.py：grep 实证零引用 → 零改动（_dispatch/TOOLS/注释均无需清理）
# tests/test_t0109_f5_tool_capability.py：计数 30→26（4 处断言 + 4 处注释/docstring）、
#   删除回归守卫 test_shell_modules_removed 追加 4 个模块（find_spec None）、
#   文件头 docstring 追加 T-0114 说明
# tests/deep_probe_v35.py：tool_*.py 计数门槛 19→15（删 2 个 tool_* 后 20→18，
#   探针预期同步，T-0113 同款维护先例；MCP expected_tools 注册表键不动）

# ── 4. 双向零缺口断言（AC-02）───────────────────────────────────────
C:/Python312/python.exe -c "…disk=glob('tools/*.py') vs TOOL_CAPABILITY_MANIFEST…"
#   manifest 26 = disk 26；missing=[] orphan=[] → DUAL-DIRECTION ZERO-GAP OK

# ── 5. 相关测试子集（AC-04 前置）────────────────────────────────────
C:/Python312/python.exe -m pytest tests/test_t0109_f5_tool_capability.py \
  tests/test_capability_registry.py tests/test_task_queue.py tests/test_evals.py \
  tests/test_t0109_f1_eval_model.py tests/test_dispatcher.py \
  tests/test_role_isolation.py tests/test_runtime_dispatch_integration.py \
  tests/test_mcp_capability.py -q
#   200 passed（含注册表 26/26 断言 + 删除回归守卫 + loop_core 实现直测）

C:/Python312/python.exe -m py_compile loop_core/capability_registry.py \
  tools/server.py tests/test_t0109_f5_tool_capability.py tests/deep_probe_v35.py
#   COMPILE OK

C:/Python312/python.exe -m pytest tests/test_live_acceptance.py tests/test_mcp_agent_runtime.py -q
#   44 passed, 3 skipped（server MCP 执行路径 LIVE）

# ── 6. 全量回归（对照基线判定）──────────────────────────────────────
C:/Python312/python.exe -m pytest tests/ -q
#   4172 passed, 64 skipped, 12 xfailed; 2 failed —— 均经 HEAD worktree
#   (6e030e6) 对照确认非本任务引入（见 removal-execution.md §5）

# ── 7. 探针基线对照 ─────────────────────────────────────────────────
C:/Python312/python.exe tests/deep_probe_v35.py
#   248 passed, 13 failed —— 与 T-0113 基线 13 FAIL 同级；唯一新增项
#   （tool_*.py 计数）经 §3 预期同步后消除，其余 13 项均为既有陈旧预期

# ── 8. 删除后零悬挂引用复核 ─────────────────────────────────────────
grep -rn -E "tool_task_queue|tool_eval|loop_vertical_slice|loop_dispatch_role" \
  --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" \
  --include="*.json" --include="*.toml" . | grep -v __pycache__ | grep -v .git \
  | grep -v .ai/evidence
#   剩余提及均为：治理登记记录（.ai/gates.yaml / .ai/task_graph.yaml /
#   .ai/tasks/*.md 审计记录，保留）、CHANGELOG.md 历史条目、
#   tests/test_t0109_f5_tool_capability.py 删除回归守卫（find_spec None 断言，
#   有意引用）—— 零 import/符号引用（AC-03）

# ── 9. 保留保护断言（硬约束 2）──────────────────────────────────────
ls agents/security-engineer/scripts/run_security_scan.py \
   agents/quality-engineer/scripts/run_quality_gates.py   # 均存在未动
grep -n "run_security_scan\|run_quality_gates" tools/server.py
#   server.py:41/61 子进程契约 + :506/508 分发点 LIVE
git diff HEAD -- hooks/   # 空（hooks/ 零改动实证）
```

## 结论

删除清单精确 4 项（B 组：tool_task_queue / tool_eval / loop_vertical_slice /
loop_dispatch_role），注册表 26/26 双向零缺口，run_* 2 个保留（server 子进程契约
LIVE），hooks/ 零改动，相关测试 200 + 44 passed，全量回归与 HEAD 基线一致。
版本 bump 与 evidence-manifest 生成留主会话执行（硬约束 5 / 遗留事项）。
