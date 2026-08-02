# F-01 handoff 生成器 idle 占位修复（AC-01）

## 根因

`.zcode/tools/continuity_producer.py` `render_handoff()`：

- L220（924bbd6 v1.0.0 引入）：`task_id = action["current_task_id"] or "none"` —— 为
  "Current Task" 展示节把 idle 态（None）替换为 `"none"` 占位字符串。
- L293（87fe5d6 v3.12.0 引入，`git log -S "evidence/none"` → bc6680f 归因，实为 v3.12.0
  渲染行 + v3.12.36 首次暴露）：`f".ai/evidence/{task_id}/..." if task_id else ...` ——
  `if task_id` 保护在 L220 之后永远为真（`"none"` 是 truthy）→ idle 态必然渲染
  `.ai/evidence/none/evidence-manifest.v1.yaml`（目录不存在 → 悬挂引用）。

idle 态 close_session 成为常态路径自 T-0101（idle 语义修复）起，首次在提交的 HANDOFF
中持续暴露该缺陷（T-0098~T-0100 均为激活态 HANDOFF，未触发）。

## 改动

`.zcode/tools/continuity_producer.py`：

1. 新增 `_latest_manifest_path(root)`：扫描 `.ai/evidence/<task>/` 下真实存在的
   manifest（复用 `_manifest_path` 的 repair 优先语义），按 `(mtime_ns, 路径)` 排序取
   最新；显式排除名为 `none` 的目录；无任何 manifest 时返回 None。仅 idles 态使用，
   激活态路径完全不经过它。
2. `render_handoff()`：拆出 `active_task_id = action["current_task_id"]`（真实 task_id，
   idle 为 None）；`task_id` 仍用于 "Current Task" 展示（格式不变）。
3. Evidence 行：`active_task_id` 存在 → 渲染当前任务 manifest（与旧行为字节一致）；
   idle（None）→ `_latest_manifest_path(root)`，取不到时渲染
   `not available (no active task)`（无悬挂引用、无 "none" 占位）。

方案选择：任务给出 A（渲染最近真实 manifest）/ B（省略）二选一，本修复采用 **A**：
idle HANDOFF 仍携带一条可解析的真实 manifest 引用（文档信息量保留，且
test_manifest_t0095 的"引用必须真实存在"断言在 idle 稳态可全绿）。

## 测试与复验

- idle worktree 端到端（`git worktree add ../loop-wt-idle HEAD`，committed
  current_task_id=null 真 idle 态）：
  - 修复前：committed HANDOFF L124 = `.ai/evidence/none/evidence-manifest.v1.yaml`；
    `test_manifest_exists_and_handoff_reference_is_real` FAILED。
  - 修复后（repair_continuity → validate_state rc=3 → close_session）：
    `Evidence manifest: .ai/evidence/T-0101/evidence-manifest.v1.yaml.`（文件真实存在），
    无 `.ai/evidence/none/`；`test_manifest_t0095` **4/4 passed**。
- 激活态行为不变：主树（T-0102 激活）HANDOFF 渲染逻辑逐字节同旧实现（`active_task_id`
  即原 `task_id`）；全量回归除 2 个已知瞬时项外 0 failed。
- 约束：未触碰 hook / runtime_controller / validate_state / audit_handoff；fail-closed
  语义零改动。

## 遗留

- 主树（激活态）HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 尚未生成
  —— 主会话完成流程创建 manifest 后自愈（AC-04 已注明）。idle 稳态下该项由本修复
  渲染最近真实 manifest，已在 worktree 实证全绿。
