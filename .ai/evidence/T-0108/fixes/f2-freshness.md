# F2 阶段 1：新鲜度检查（T-0108 线 5）— 证据

- 目标文件：`loop_core/projection_engine.py`（视图生成，state.yaml 派生）、`.zcode/tools/validate_state.py`（仅新增只读告警）
- 依据：design-bh-integration.md F2 阶段 1（只读：validate_state 加新鲜度检查 + 投影视图生成）；任务卡 AC-04/AC-05

## 改动

1. **loop_core/projection_engine.py（F2-1 视图生成，纯函数不写盘）**
   - `generate_state_view(project_root)`：从 state.yaml 派生视图（schema=state-view/v1；phase/current_task_id/current_gate_id/loop_mode/last_handoff_at 逐字段回源）；`task_status` 派生自 task_graph.yaml（任务卡 Status 的权威源是 task_graph，视图只读派生不手改）；`derived_summary` 人读摘要
   - `write_state_view(project_root, view=None)`：显式落盘 `.ai/views/state-view.yaml`（F2-1 阶段仅显式调用才写；validate_state 本身只读）
   - `is_state_view_stale(project_root, tolerance_seconds=1.0)`：state.yaml mtime vs 视图 mtime；视图缺失 → (False, None)
   - 与既有 PROJECT_MAP 投影引擎共存（不动原 RoleProjection/ProjectionEngine 逻辑）

2. **.zcode/tools/validate_state.py（仅新增只读告警路径）**
   - `check_state_view_freshness(root, base)`：`.ai/views/state-view.yaml` 存在且 mtime 早于 state.yaml（>1s 容差）→ `[warn] stale view: ... 仅告警不阻断`；视图缺失/不可读 → 空（无视图可比不告警）
   - 接入 main() 第 8 步 `errors.extend(check_state_view_freshness(root, base))` — warn 前缀自动分流到 warn 流，**不进入 blocker 判定、不改变 exit code**
   - **diff 纯新增零删除**：`git diff HEAD -- .zcode/tools/validate_state.py | grep "^-"` 为空（硬约束 3 实证）

## 测试

- `tests/test_projection_freshness.py`（8 用例，见 f8-contract-tests.md）
- `tests/test_t0108_fixes.py` TestValidateStateRegression：真实仓库 validate_state exit 0 + `[ok] state is usable` + 无 stale 告警（默认路径零干扰）
- 手工实证：伪造旧 mtime 视图（os.utime -3600s）→ validate_state 输出 `[warn] stale view`，error 集合（15 条）与 exit code（2）与无视图时完全一致

## 约束自查（硬约束 3/4）

- 既有判定与 exit code 语义零变化：新检查结果只追加 `[warn]` 前缀条目（既有分类逻辑 warn_errors/blocker_errors 分流），测试证明 error 集合与 exit code 逐条一致
- F2-1 仅告警不阻断：stale view 不进入 blocker，不改变 fail-closed 语义
- 防篡改：视图是派生产物（只读生成），不参与语义哈希；continuity 源清单不含视图
- 不实施 F2-2（写入收敛/任务卡 Status 派生接管）：视图写入仅在显式调用时发生，无任何自动写路径

## 遗留

- `.ai/views/state-view.yaml` 由主会话/后续会话按需显式生成（write_state_view）；T-0109（F2-2）将把写路径收敛并自动刷新视图
