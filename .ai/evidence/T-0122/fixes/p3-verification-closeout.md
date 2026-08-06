# T-0122 修复记录：p3-verification-closeout

## 背景

T-0122 原计划实施 T-0104 P3 建议类 4 项。执行中核实发现：**4 项已全部由
T-0105 批 2（B-4-1~4）实施**（test_t0105_batch2.py 21 个测试锁定）。本任务
调整为核实关闭——零产品代码改动，修正 T-0116 的重复登记。

## 逐项核实表（B-4-1~4 ↔ T-0104 P3）

| T-0104 P3 建议 | T-0105 落地 | 代码/测试证据 | 核实 |
|----------------|------------|--------------|------|
| 记忆召回无任务/门过滤 | B-4-1 | `context_packager.build_context` 新增 memory_gate_id/memory_tag 参数；`recall(task_id=..., gate_id=..., tag=...)` 透传（None=不过滤，与 T-0104 现状一致） | ✅ |
| phases 误写字符串逐字符展开 | B-4-2 | `role_orchestrator._validated_phases`：非 list/非法元素 → 整体回退 disabled（fail-closed） | ✅ |
| evidence-manifest 时序依赖 | B-4-3 | `.ai/CONTRACTS.md` Completion Flow Conventions：先 manifest → 再 HANDOFF → 最后 test_manifest_t0095 | ✅ |
| 每次派发重读配置 | B-4-4 | `_CONFIG_CACHE` 按 (路径, mtime) 缓存，mtime 变化才重读；失败清缓存回退 | ✅ |

测试存在性：`tests/test_t0105_batch2.py`（B-4-1×7 / B-4-2×9 / B-4-4×5 / B-4-3×1 = 21）。

## 登记修正

- `.ai/KNOWN_ISSUES.md`：T-0104 P3 建议类条目 → 标注"4 项均已由 T-0105 批 2
  实施，T-0116 重复登记"。
- `.ai/evidence/T-0116/fixes/p3-wording-fixes.md`：补充重复登记说明。

## 教训（学习回路）

T-0116 登记"建议类不实施"前未 grep T-0105 证据目录（T-0105 批 2 标题即
"P3 四项"）——登记前应全仓检索实施痕迹（grep fixes/commands + 代码符号）。

## 验证

- `test_t0105_batch2.py` 21 passed（B-4-1~4 落地实证）
- 全量回归结果见 commands.md；产品代码零改动
