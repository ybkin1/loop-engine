# 批 3 批次证据 —— 开关 + 调用点（设计-5 记忆注入）

> 任务：T-0104 | 日期：2026-08-02 | 落地依据：D-03 §5.3.2 / §5.3.3

## 改了什么（3 个目标文件 + 1 个转发管道）

| 路径 | 改动点 | 设计编号 |
|---|---|---|
| `skills/loop-governance/config.yaml` | 新增 `memory_injection: {enabled: true, phases: ["S4","S5","S6","S8","S9","S10"], memory_limit: 5}`（D-03 §5.3.2 回退方案原文；非 hook 配置，附注释说明回退语义） | 5 |
| `loop_core/role_orchestrator.py` | 新增 `_load_memory_injection_config`（候选：skills/loop-governance/config.yaml，其次 .zcode 安装副本；缺失/损坏/非法 → disabled = fail-closed）与 `_memory_injection_for(phase, root)`（阶段前缀匹配："S4-implementation" ↔ 配置 "S4"）；`build_dispatch_manifest` 对 config phases 内阶段显式传 `include_memories=True, memory_limit=N`；enabled=false 时传 `(False, 5)`，行为与现状完全一致 | 5 |
| `loop_core/context_packager.py` | `build_context` 新增关键字参数 `include_memories=False, memory_limit=5`（默认 False → 逐字节现状）；开启时经 memory_service.recall + memories_to_context 追加"相关经验（Related Memories）"节（渲染格式与 context_loader.py L945-980 一致：空召回 no-op；store 损坏抛 KnowledgeStoreError = fail-closed，与 context_loader 语义一致） | 5 |
| `loop_core/role_loader.py`（管道） | `build_role_context` / `load_role_prompt_with_context` 新增可选关键字 `include_memories=False, memory_limit=5` 透传 context_packager（默认 False 时与现状逐字节一致）。说明：该文件不在 D-03 §6 清单内，属"调用点显式传参"机制的最小传递路径（plumbing），已在 commands.md 遗留事项注明 | 5 |

**刻意不动的文件**：`loop_core/context_loader.py`（L806/L1122 `include_memories: bool = False`
默认值保持 False，全部现有调用与测试不受影响）；hooks/ 零改动。

## 测试结果

`tests/test_memory_injection.py`（新增，14 项）：

| 覆盖点 | 结果 |
|---|---|
| enabled=true + phases → S4 注入 (True, 5)；S3/S11 不注入 (False, 5) | 通过 |
| enabled=false → (False, 5)（行为与现状完全一致） | 通过 |
| 配置缺失 / YAML 损坏 → fail-closed (False, 5) | 通过 |
| 阶段前缀匹配（"S4-implementation" ↔ "S4"） | 通过 |
| memory_limit 覆盖（3） | 通过 |
| build_dispatch_manifest：S4 → include_memories=True, limit=5；S3 → False；enabled=false → [(False,5)]（monkeypatch 捕获 kwargs） | 通过 |
| build_context：默认无记忆节；True 时含"## 相关经验（Related Memories）"；limit=2 只注入 2 条；空 store no-op；store 损坏抛 KnowledgeStoreError | 通过 |

回归：`test_context_loader.py`（39 项）全部通过 —— context_loader 默认值路径零影响。

## 约束自查（git diff）

- `git diff --stat -- loop_core/context_loader.py` → 空（默认参数零改动）
- `git diff --stat -- hooks/` → 空
- `git diff --stat -- loop_core/enforcement.py loop_core/hard_constraints.py
  loop_core/guard_health.py loop_core/state_machine.py` → 空（治理内核零触碰）
- fail-closed 语义不变：配置缺失/损坏 → 不注入（现状）；store 损坏 → 异常而非猜测

## 回退

`memory_injection.enabled: false` 一键回退到现状；先降 memory_limit（5→3→0）再整体关闭；
记忆注入为纯附加节，无状态迁移（D-03 §5.4）。
