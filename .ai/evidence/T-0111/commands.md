# T-0111 执行命令日志（developer 子代理段）

日期：2026-08-03
任务卡：`.ai/tasks/T-0111.md`（排布收官：修复器治理 + 臃肿全景清理验证）

## 已执行命令（可复现）

```bash
# ── 1. 基线确认 ──────────────────────────────────────────────────────
C:/Python312/python.exe -m pytest tests/test_observability.py \
  tests/test_execution_ledger.py tests/test_governance_metrics.py \
  tests/test_ai_doc_links.py -q        # 94 passed（改动前基线）

# ── 2. 实现后专项测试 ────────────────────────────────────────────────
C:/Python312/python.exe -m pytest tests/test_repair_governance.py -q
#   20 passed（AC-01 两分支 / AC-02 归类 / AC-03 兜底边界 + 端到端）

C:/Python312/python.exe -m pytest tests/test_execution_ledger.py \
  tests/test_observability.py tests/test_repair_governance.py -q
#   79 passed（D3-3 归档保留+跨链延续 7 项 / D4-6 读侧计数 4 项）

# ── 3. 既有消费者回归（observability/metrics/guard-events 相关）──────
C:/Python312/python.exe -m pytest tests/test_governance_metrics.py \
  tests/test_manifest_t0095.py tests/test_t0110_batch_b1.py \
  tests/test_ai_doc_links.py tests/test_guard_health.py \
  tests/test_self_audit_llm.py tests/test_t0109_f5_tool_capability.py \
  tests/test_t0105_batch3.py -q      # 139 passed（见遗留事项 3 项基线失败）

# ── 4. golden 表面基线更新（T-0111 有意新增 6 名，见 fixes/repair-metrics.md）
C:/Python312/python.exe .ai/evidence/T-0110/golden/generate_golden.py \
  .ai/evidence/T-0110/golden/golden-before.json
#   git diff：仅 dir_snapshots.governance_metrics +6 行（无其他漂移）

# ── 5. 编译检查 ──────────────────────────────────────────────────────
C:/Python312/python.exe -m py_compile loop_core/observability.py \
  loop_core/governance_metrics.py loop_core/execution_ledger.py \
  .zcode/tools/validate_state.py .zcode/tools/close_session.py \
  tests/test_repair_governance.py tests/test_execution_ledger.py \
  tests/test_observability.py          # COMPILE_OK

# ── 6. 全量回归（后台）───────────────────────────────────────────────
C:/Python312/python.exe -m pytest tests/ -q --ignore=tests/deep_probe_v35.py
#   结果见"全量回归"节

# ── 7. 死工具复核（调用图证据，T-0109 tool-removal-candidates.md）────
grep -rn "tool_quality_gates\|tool_security_scan\|tool_dependency_analysis\|tool_contract_validate\|tool_cost_tracker\|tool_evidence_chain\|tool_task_queue\|tool_eval\|loop_vertical_slice\|loop_dispatch_role" --include="*.py" . | grep -v __pycache__ | grep -v .ai/evidence | grep -v tests/
grep -rn "run_security_scan\|run_quality_gates" tools/server.py
#   结论见 fixes/final-audit.md（复核结论表 + 删除建议，待用户独立 gate）

# ── 8. 注册表终态审计 ────────────────────────────────────────────────
C:/Python312/python.exe -c "from loop_core.capability_registry import all_tool_names; from pathlib import Path; files={p.stem for p in Path('tools').glob('*.py')}; m=set(all_tool_names()); assert len(files)==len(m)==36 and files==m"
#   36 = 36 全覆盖，双向零缺口

# ── 9. 兜底边界实测（repair_continuity.py 零改动只读验证）────────────
# tests/test_repair_governance.py::TestFallbackBoundaries 5 项全绿：
#   dynamic_only 不重算 semantic_sha256/source_sha256（哈希值不变可观测）
#   全量模式对照组 source_sha256 变化；非 repair SOURCE_DRIFT exit 2 且
#   零 repair 事件；dynamic_only 唯一写文件 = project_continuity.yaml
```

## 全量回归

| 项 | 结果 |
|----|------|
| 专项（test_repair_governance） | 20 passed |
| D3-3/D4-6（execution_ledger + observability） | 79 passed（含既有） |
| 既有消费者集（metrics/b1 golden/manifest/doc-link/guard_health/self_audit/f5/batch3） | 136 passed，3 failed 均为**基线既有失败**（见遗留事项） |
| golden 逐字节等价（test_golden_metrics_byte_identical） | 通过（MetricsReport 零改动） |
| 全量 `pytest tests/`（排除 deep_probe_v35） | 4170 passed / 4 failed（3 项基线既有 + 1 项本任务修复后转绿，见下） |
| 编译 | 全部改动文件 COMPILE_OK |

**中途发现并修复（T-0109 F2-2 写收敛门）**：`_record_repair_event` 的
`f.write(...)` 使 `validate_state.py` 被静态扫描判为"state 写路径候选"
（文件本含 `"state.yaml"` 字面量）→ `test_all_state_write_candidates_registered`
失败。已按测试机制在 `NON_STATE_WRITERS` 登记
`.zcode/tools/validate_state.py`（事件日志写 guard-events.jsonl，非状态
五写）——与 `hooks/scripts/loop_enforcement.py`（guard-events 计数文件）
同类登记。`test_categories_are_disjoint` 保持（close_session 已在
SANCTIONED_WRITERS，不重复登记）。该测试现全绿（13 passed）。

## 遗留事项（非本任务引入，交主会话复核）

1. `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`：
   HANDOFF.md 引用 `.ai/evidence/T-0111/evidence-manifest.v1.yaml` 尚未创建
   ——T-0111 进行中状态产物，closeout 生成后自愈（git stash 验证基线即失败）。
2. `test_t0109_f5::test_hooks_only_whitelist_file_changed`：断言工作树
   hooks/ 相对 HEAD 恰有一处改动——T-0110 已提交，diff 为空（基线即失败，
   状态型断言，提交本任务后恢复"仅 loop_enforcement.py"语义）。
3. `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed`：
   service.startup 因本机 localhost:3000/8080 有服务可达而 PASS（环境相关，
   基线即失败）。

## 约束自查

- hooks/ 零改动：`git status -- hooks/` 无条目（基线即有，未触碰）。
- `repair_continuity.py` 零改动：未列入 git status；测试只读调用其函数。
- 治理内核判定零触碰：validate_state/close_session 仅加 `_record_repair_event`
  旁路写入（try/except 吞错），无任何判定/exit code 变更；fail-closed 语义
  由 AC-03 测试断言（非 repair SOURCE_DRIFT 仍 exit 2）。
- 不执行任何工具删除：本任务仅复核+建议（fixes/final-audit.md），删除待
  用户独立 gate。
- 写路径仅限任务卡 allowed_paths（.ai/、loop_core×3、.zcode/tools×2、
  tests/、golden 属 .ai/）。
- 版本文件未改（bump 3.12.48 由主会话执行）。
