# T-0109 F2-2 状态写入收敛 — 修复证据

## 改动

### 1. `.zcode/tools/governor_lib.py`（保护区，纯新增 ~90 行）
- `STATE_RELATED_FILES = ("state.yaml", "task_graph.yaml", "HANDOFF.md", "PROGRESS.md")`
  + tasks/ 目录——静态检查「仅 governor_lib 写 state 相关路径」的覆盖清单。
- `refresh_state_view(root) -> bool`：复用 T-0108 `loop_core.projection_engine.write_state_view`
  刷新派生视图 `.ai/views/state-view.yaml`；独立运行环境（loop_core 不可导入）时
  补 repo root 到 sys.path 后导入；失败显式 `logging.warning(STATE_VIEW_REFRESH_FAILED)`，
  返回 False（不静默吞错，不阻断已提交的权威写）。
- `write_state_files(root, changes, *, refresh_projection=True, **kwargs)`：F2-2
  收敛写入入口。每个路径必须解析在 `.ai/` 内且属于 state 相关文件
  （state.yaml / task_graph.yaml / HANDOFF.md / PROGRESS.md / tasks/*.md），
  否则 `GovernanceError("SCOPE_VIOLATION", ...)`（fail-closed）；内部调用既有
  `transactional_write_texts`（journal 回滚 + 幂等表机制，T-0089 U7 语义保持）；
  默认写后刷新派生视图；其余 kwargs（idempotent/retry/stale_timeout_seconds）
  原样透传。默认（非 idempotent）模式返回 `TransactionResult(written=changes 路径)`
  ——兼容底层返回 None 的遗留语义，保证调用方总能拿到写入结果。

### 2. `loop_core/state_machine.py`（仅加刷新调用，判定零改动）
- `atomic_write_state`：保持 .tmp + os.replace 原子写（design F2-2「:580 唯一权威
  写入入口，保持」）；写入后新增一行 `_refresh_state_view_after_transition(root_p)`。
- 新增 `_refresh_state_view_after_transition(root_p)`：转换后触发 projection 刷新；
  best-effort——刷新失败 `warnings.warn("STATE_VIEW_REFRESH_FAILED: ...")` 显式告警，
  不回滚已提交的状态转换（fail-closed 语义不变）。

### 3. `.zcode/tools/validate_state.py`：零改动
F2-1（T-0108）既有的 `check_state_view_freshness` 即双写检测器（视图 mtime 早于
state.yaml >1s → `[warn] stale view`，仅告警不改判定）。F2-2 的收敛写路径使
视图随写刷新 → 告警清零（测试实证），无需新增检测函数（任务书「若需配合」未触发）。

## 测试（tests/test_t0109_f2_write_convergence.py，13 passed）

- **TestStaticWriteConvergence（AC-02）**
  - 仓库级 AST 扫描：所有「代码级 state 路径字面量 + 写操作」文件必须登记在
    SANCTIONED_WRITERS（governor_lib/close_session/install/upgrade/
    state_machine/projection_engine）、LEGACY_WRITERS（executor/
    runtime_controller/zcode_adapter/loop_auto_activate，各附理由）、
    MANIFEST_REPAIR_WRITERS（repair_continuity）、NON_STATE_WRITERS
    （dashboard_views/evals/slo_gate/guard_health/hook_common/loop_enforcement/
    role_isolation/session_brief/loop_onboard）之一；未登记 → FAIL。
  - 四类互斥；.zcode/tools 与 scripts 收敛入口必须引用 governor_lib 事务写
    （transactional_write_texts / write_state_files）。
  - loop_core 中 state.yaml 写路径集合 == 登记名单（state_machine = 唯一权威
    入口；executor/runtime_controller = 遗留；projection_engine = 视图写；
    guard_health = 自测 fixture）——新增写路径即测试失败。
- **TestProjectionRefreshOnStateWrite**：atomic_write_state 与 write_state_files
  写后 `.ai/views/state-view.yaml` 自动生成且内容反映新状态（phase 回源断言）；
  is_state_view_stale False；刷新失败（monkeypatch 抛异常）→ 权威写已提交 +
  pytest.warns(STATE_VIEW_REFRESH_FAILED)；write_state_files 拒绝 gates.yaml
  （非 state 路径）与 `.ai` 外路径（SCOPE_VIOLATION）；接受任务卡 tasks/T-*.md
  与 HANDOFF.md；idempotent=True 幂等去重（written→skipped）。
- **TestDualWriteWarningZeroed**：裸写 state.yaml 不刷新 → `[warn] stale view`
  仍在（检测器有效）；收敛写（atomic_write_state）→ 告警清零；validate_state
  子进程集成：收敛写后输出无 stale（双写告警清零实证）。

## 约束自查

| 硬约束 | 实证 |
|--------|------|
| hooks/ 零改动 | `git diff HEAD -- hooks/` = 0 行 |
| 内核判定零触碰 | state_machine.py diff 仅刷新调用 + 新 helper（见 git diff，判定零改动）；gate_guard/enforcement/hard_constraints/guard_health 未触碰 |
| state_machine 仅加刷新调用 | diff 实证：atomic_write_state 主体原样，末尾加 `_refresh_state_view_after_transition(root_p)` |
| validate_state 仅只读检测 | diff = 0 行（未改动） |
| fail-closed 不变 | 写失败抛错不回滚；刷新失败显式告警不静默；非 state 路径 SCOPE_VIOLATION |
| 写路径限 allowed_paths | 仅 governor_lib.py / state_machine.py / tests/ / .ai/ |
| 版本文件不改 | pyproject/CHANGELOG 未触碰（bump 主会话） |

## 回归（相关既有测试）

- test_state_machine_enhanced / test_projection_engine / test_projection_freshness /
  test_reliable_delivery / test_executor：全绿（test_t0108_fixes 中 2 项 validate_state
  实仓回归因 F3 continuity drift 报 exit 2——预期，主会话 repair 后恢复，见 commands.md 遗留）
- py_compile 全部通过。

## 遗留

- 主会话收尾：repair_continuity（gates.yaml drift）+ close_session（HANDOFF 收敛）
  ——F2-2 的 state-view.yaml 已随权威写自动刷新，无需额外生成。
