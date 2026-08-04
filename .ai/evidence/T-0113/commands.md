# T-0113 执行命令日志（developer 子代理段：死工具删除）

日期：2026-08-03
任务卡：`.ai/tasks/T-0113.md`（用户 gate 批准的 A 组 6 薄壳 + C 组 2 legacy = 8 文件删除）
复核依据：`.ai/evidence/T-0111/fixes/final-audit.md`

## 已执行命令（可复现）

```bash
# ── 0. 基线：删除前 git HEAD 确认 ────────────────────────────────────
git log --oneline -1        # 3623584 v3.12.48（回滚提交点）
git status --short          # 确认预存改动（.ai/HANDOFF.md 等主会话改动，本任务不动）

# ── 1. 删除 8 个文件（精确清单，git rm 原子暂存）────────────────────
git rm tools/tool_quality_gates.py tools/tool_security_scan.py \
        tools/tool_dependency_analysis.py tools/tool_contract_validate.py \
        tools/tool_cost_tracker.py tools/tool_evidence_chain.py \
        scripts/evidence_chain.py scripts/security_scan.py
git diff --cached --name-status --diff-filter=D   # 恰 8 项 D（AC-01）

# ── 2. 引用同步写路径（allowed_paths 内）────────────────────────────
# loop_core/capability_registry.py：manifest 删 6 条目 + 头注释 36→30
# tools/server.py：_dispatch 确认内联（无被删模块 import）→ 仅注释清理
# tests/test_t0109_f5_tool_capability.py：36→30、等价测试→LIVE 断言、
#   删除回归守卫（find_spec None）、证据链收敛测试改为 loop_core 直测
# tests/deep_probe_v35.py：TOOL_MODULES 删 6 项（MCP expected_tools 保留）
# docs/06-delivery.md：2.3 删 6 行、2.7 删 evidence_chain 行
# docs/ops-handoff.md：安全监控命令改指 agents/.../run_security_scan.py

# ── 3. 双向零缺口断言（AC-02）───────────────────────────────────────
C:/Python312/python.exe -c "…disk=glob('tools/*.py') vs TOOL_CAPABILITY_MANIFEST…"
#   manifest 30 = disk 30；missing=[] orphan=[] → DUAL-DIRECTION ZERO-GAP OK

# ── 4. 相关测试子集（AC-04 前置）────────────────────────────────────
C:/Python312/python.exe -m pytest tests/test_t0109_f5_tool_capability.py \
  tests/test_evidence_chain.py tests/test_quality_gates.py \
  tests/test_security_scan_whitelist.py tests/test_security_dependency_scan.py -q
#   131 passed（含 MCP 内联键 LIVE 断言 + 删除回归守卫）

C:/Python312/python.exe -m compileall -q loop_core/capability_registry.py \
  tools/server.py tests/test_t0109_f5_tool_capability.py tests/deep_probe_v35.py
#   COMPILE OK

# ── 5. 全量回归（对照基线判定）──────────────────────────────────────
C:/Python312/python.exe -m pytest tests/ -q
#   4172 passed, 64 skipped, 12 xfailed; 2 failed —— 均经 HEAD worktree
#   (3623584) 对照确认为既有/环境失败，非本任务引入（见 removal-execution.md §5）

# ── 6. 删除后零悬挂引用复核 ─────────────────────────────────────────
grep -rn …tool_quality_gates|tool_security_scan|tool_dependency_analysis|
    tool_contract_validate|tool_cost_tracker|tool_evidence_chain…（全仓，除 .ai/evidence/）
grep -rn …scripts.evidence_chain|scripts/evidence_chain|scripts.security_scan|
    scripts/security_scan…（全仓，除 .ai/evidence/）
#   剩余提及均为：历史证据（保留）、任务卡、测试删除回归断言（find_spec None）、
#   注释/允许清单字符串（hooks 注释、loop_core.evidence_chain 注释、agents 排除表）
#   —— 零 import/符号引用（AC-03）
```

## 结论

删除清单精确 8 项（A 组 6 + C 组 2），注册表 30/30 双向零缺口，
MCP 内联注册表键（quality_gates_run/security_scan_run/dependency_analysis/
contract_validate/evidence_verify/evidence_freeze/cost_report）LIVE 断言全绿，
相关测试 131 passed，全量回归与 HEAD 基线一致。版本 bump 与 evidence-manifest
生成留主会话执行（硬约束 5 / 遗留事项）。
