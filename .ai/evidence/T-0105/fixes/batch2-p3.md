# T-0105 批 2：T-0104 P3 四项修复证据（batch2-p3.md）

> 日期：2026-08-03 ｜ 执行者：developer 子代理
> 依据：`.ai/evidence/T-0104/review/independent-review.md` 第六节（P3 ×4）

## B-4-1 记忆召回过滤（recall task_id/gate_id/tag 透传）

**问题**（P3-1）：`context_packager.build_context` 中 `recall(root, limit=memory_limit)` 未传过滤参数，S4+ 注入全局最新 N 条（newest-first），可能注入跨任务不相关记忆；D-03 §5.4 与 context_loader（`_apply_memory_injection` 传 `task_id=memory_task_id`）均为"按任务/gate/标签检索"。

**修复**：
- `loop_core/context_packager.py`：
  - `build_context` 新增关键字参数 `memory_gate_id: str | None = None`、`memory_tag: str | None = None`
  - 召回调用改为透传：`recall(root, limit=memory_limit, task_id=task_id or None, gate_id=memory_gate_id, tag=memory_tag)`
  - fail-closed 保持：任一过滤参数为 None/空 → 不过滤（与 T-0104 现状逐字节一致）；空召回 no-op；store 损坏仍抛异常
- `loop_core/role_orchestrator.py`：`build_dispatch_manifest` 派发 S4+ 时当前 `task_id` 已沿既有管道（load_role_prompt_with_context → build_role_context → build_context）透传，本次在调用点加注释明确"task_id 同时作为记忆召回过滤"，消除跨任务注入。

**测试**（`tests/test_t0105_batch2.py::TestRecallFilteringB41`，7 个）：task_id 隔离（T-00A 只召回本任务）；无 task_id = 不过滤（现状一致）；gate_id 过滤；tag 过滤；task_id+tag AND 组合；include_memories=False 零行为变化；dispatch 透传 task_id 断言。

## B-4-2 memory_injection 配置校验

**问题**（P3-2）：phases 误写为字符串（如 `"S4"`）会被逐字符展开为 `["S","4"]` 永不匹配；memory_limit 非法值靠 except 兜底。行为方向安全但无 schema 校验。

**修复**（`loop_core/role_orchestrator.py`）：
- 新增 `_validated_phases(value)`：非 list（字符串/tuple/None）→ 返回 None → 整体回退 disabled 默认（fail-closed，杜绝逐字符展开）
- 新增 `_validated_memory_limit(value)`：bool/非数字 → 默认 5；int() 转换失败 → 默认 5；`<=0` → 默认 5；正浮点 int() 截断（沿用现状 int() 语义）
- `_load_memory_injection_config` 集成：phases 非法 → 整体回退 `{"enabled": False, "phases": [], "memory_limit": 5}`；memory_limit 非法仅该字段回退 5

**测试**（`TestConfigValidationB42`，9 个）：字符串 phases 回退 disabled；list 正常；phases 缺失/空 → []；limit 0/负数/字符串/bool → 5；浮点截断；validator 单元；损坏 YAML fail-closed。

## B-4-3 evidence-manifest 时序约定文档化

**问题**（P3-3）：HANDOFF 对 manifest 的引用在清单生成前会使 `test_manifest_t0095` 暂时失败；后续任务若在 evidence 管线产出前更新 HANDOFF 会再现同类时序失败。

**修复**：写入 `.ai/CONTRACTS.md` 新增 `## Completion Flow Conventions` 节（**选此位置的原因**：CONTRACTS.md 是主会话必读的权威约定文档、位于 .ai/ 允许写入面，且不触碰 skills/ 安装副本同步面）：

> 主会话收尾顺序固定为：先创建/重生成 evidence-manifest（create-only）→ 再更新 HANDOFF 中的 manifest 引用 → 最后才跑 `test_manifest_t0095`。HANDOFF 引用先于清单生成会导致该测试暂时失败（悬挂引用），属时序错误而非清单缺陷。

**测试**（`TestManifestTimingConventionB43`，1 个）：断言 CONTRACTS.md 含约定文本（Completion Flow Conventions / evidence-manifest / test_manifest_t0095 / HANDOFF）。

## B-4-4 配置读盘缓存

**问题**（P3-4）：`_load_memory_injection_config` 每次 `build_dispatch_manifest` 调用都读盘解析 YAML（两个候选路径）。

**修复**（`loop_core/role_orchestrator.py`）：
- 模块级缓存 `_CONFIG_CACHE: dict[str, tuple[int, dict]]`（key = 配置绝对路径，value = (mtime_ns, cfg)）
- 首次读盘解析并缓存；mtime 相同 → 缓存命中直接返回（拷贝防外部改动）；mtime 变化 → 重读
- 读取/解析失败 → 清缓存条目并回退 fail-closed 默认（损坏结果不驻留）
- 两候选路径（repo 源 `skills/loop-governance/config.yaml`、安装副本 `.zcode/skills/loop-governance/config.yaml`）各自独立缓存

**测试**（`TestConfigDiskCacheB44`，5 个）：首次读盘；同 mtime 内容变化仍返回旧值（命中）；mtime 变化重读新值；失败清缓存 + 修复后可重新读盘；首候选缺失时用安装副本。

## 测试结果

| 范围 | 结果 |
|------|------|
| 新增 `tests/test_t0105_batch2.py` | **21 passed**（B-4-1×7 / B-4-2×9 / B-4-3×1 / B-4-4×5） |
| 相关既有测试（test_memory_injection / test_knowledge_memory / test_context_loader / test_context_compression） | **153 passed，0 failed**（无回归） |
| py_compile（context_packager / role_orchestrator / 新测试） | PASS |
| 全量回归（3842 passed + 2 failed + 64 skipped + 12 xfailed） | 2 failed 均为**基线/瞬态问题，非本次改动引入**（见下） |

## 全量回归 2 failed 归因（与本批改动无关）

1. `test_release_bump.py::test_bump_invalid_version_is_usage_error`：**基线即失败（HEAD 复验确认）**——测试硬编码断言 `load_version == "3.12.41"`，而 T-0104 bump 后 repo 已为 3.12.42（HEAD 提交 da4fb18 的 pyproject.toml = 3.12.42；本次改动零触碰版本载体）。属 T-0104 收尾遗留的陈旧断言，应在 T-0105 收尾（bump 3.12.43 时）一并修正。
2. `test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real`：**B-4-3 记录的已知时序瞬态**——T-0105 激活后 close_session 按 `render_handoff` 逻辑渲染当前任务 manifest 引用 `.ai/evidence/T-0105/evidence-manifest.v1.yaml`（尚未创建，收尾时由 evidence 管线生成）；HEAD 基线该测试通过（引用 T-0104 已存在 manifest）。主会话按 B-4-3 新约定收尾（先建 manifest → 再更新 HANDOFF 引用 → 再跑该测试）即可消除，无需本批改动。

## 约束自查

| 检查项 | 结果 |
|--------|------|
| `git diff --stat -- hooks/` | **空**（零改动，仅只读验证） |
| `git diff --stat -- loop_core/context_loader.py` | **空**（默认值不动） |
| loop_core 改动文件 | 仅 `context_packager.py`、`role_orchestrator.py`（T-0104 P3 指定的落地文件）；治理内核（gate_guard/enforcement/hard_constraints/state_machine/…）零触碰 |
| fail-closed 语义 | 配置缺失/损坏/非法 → 回退 disabled 默认（有测试）；空召回 no-op；store 损坏抛异常（既有测试保持） |
| validate_state | 0 legacy warn、无连续性漂移、`[ok] state is usable`、exit 0 |
