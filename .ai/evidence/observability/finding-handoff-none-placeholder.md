# Finding: handoff 生成器 idle 占位缺陷（.ai/evidence/none/ 悬挂引用）

- 记录时间：2026-08-02（T-0101 提交后 idle 稳态复验发现）
- 状态：OPEN（待用户裁决是否立项修复）
- 优先级：P3（不阻断 release check / 不涉及约束；造成 test_manifest_t0095 持续性失败 + idle 态 HANDOFF 文档缺陷）

## 现象

idle 稳态（current_task_id=null）下运行 `close_session.py` 生成的 `.ai/HANDOFF.md` 中，Evidence manifest 引用被渲染为 `.ai/evidence/none/evidence-manifest.v1.yaml`（"none" 占位路径，目录不存在）→ `tests/test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real` 失败（悬挂引用）。

## 根因

- `git log -S "evidence/none"` 定位：**bc6680f（v3.12.36，T-0097）引入**。idle/无任务态 handoff 生成流程以 task_id=None 写 "none" 占位路径。
- T-0098/T-0099/T-0100 提交的 HANDOFF 均为**激活态** close_session 生成（引用真实任务 manifest → 存在 → 测试通过）；T-0101 是**首个在 idle 稳态生成并提交 HANDOFF** 的任务（idle 语义修复使 idle 态 close_session 成为常态路径），首次暴露该缺陷。
- 归因修正：T-0100 验收报告中"生成 manifest 后 test_manifest_t0095 自愈"的归因**有误**——T-0100 提交的 HANDOFF 是激活态生成（引用 T-0100 manifest），与 manifest 生成无关；T-0098~T-0100 期间该项从未真正失败过，T-0101 是首次持续失败。T-0101 acceptance-report 第七节已如实记录。

## 影响

1. `test_manifest_t0095` 在 idle 态 HANDOFF 提交后必失败（全量回归 1 failed 噪音）
2. idle 态生成的 HANDOFF 文档携带无效 manifest 引用（文档缺陷）
3. 不阻断 release check（key_tests 不含该项）、不涉及任何约束语义

## 修复方向（若立项）

- 定位 handoff 生成器（governor_lib/close_session 的 HANDOFF 渲染逻辑，bc6680f 变更处）：idle 态 task_id=None 时 manifest 引用渲染为**实际存在的最近任务 manifest 或省略该字段**（而非 "none" 占位）
- 补测试：idle 态 close_session 生成的 HANDOFF 无悬挂引用（test_manifest_t0095 全绿）

## 证据

- .ai/HANDOFF.md（c4426c6/ff94df1 提交版，L124 附近 "Evidence manifest: .ai/evidence/none/evidence-manifest.v1.yaml"）
- tests/test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real
- git log -S "evidence/none" → bc6680f（v3.12.36，T-0097）
- .ai/evidence/T-0101/acceptance/acceptance-report.md 第七节（复验记录与根因分析）
