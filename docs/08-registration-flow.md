# 登记流程标准步骤（T-0127 P0）

> 治理文件（state/gates/task_graph/HANDOFF/project_continuity）变更后的标准收尾，
> 消除"每次变更都要手工 --repair + 手工 render_handoff"的高频摩擦。

## 标准步骤（一步完成）

治理文件变更完成后，运行：

```
C:/Python312/python.exe .zcode/tools/validate_state.py --auto-sync .
```

`--auto-sync` 依次完成（单次执行内收敛，幂等）：

1. **校验**：完整状态校验（与普通运行一致）
2. **修复**：若 continuity 源哈希漂移（state/gates/task_graph 等变更引起），
   自动 `repair_continuity`（等价于原 `--repair`）
3. **重生成**：`render_handoff` 重新生成 HANDOFF（确定性输出，与当前结构化
   状态一致）
4. **同步**：若 HANDOFF 属于 continuity 源集，同步其记录哈希（无副作用，
   幂等）

## 效果

| 场景 | 旧流程（手工两步） | 新流程 |
|---|---|---|
| 登记任务后 | validate → 报漂移 → `--repair` → render_handoff → 再 validate | 一次 `--auto-sync` |
| 推进任务状态后 | 同上 | 一次 `--auto-sync` |
| 批准 gate 后 | 同上 | 一次 `--auto-sync` |

## 顺序依赖说明（实测教训）

`render_handoff` 依赖 continuity 有效：若先 render 后 repair 会直接抛
`GovernanceError: Continuity source drift`。`--auto-sync` 内部固定
**先 repair 后 render**（validate_state.py §5 修复 → T-0127 auto-sync 块），
顺序不可调换。

## 边界

- `--auto-sync` 只处理确定性漂移（continuity 哈希 / HANDOFF 投影），
  **不覆盖**人工修正的治理文件内容
- 仍会如实报告真实损坏（不可解析 YAML 等）→ 走 D-03 二级恢复路径
- 登记动作（任务卡/task_graph/gates 写入）仍由登记人完成，auto-sync 只是
  登记后的标准收尾
