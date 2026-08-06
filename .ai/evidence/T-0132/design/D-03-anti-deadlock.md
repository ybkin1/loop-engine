# D-03: 防异常锁死机制设计（硬约束 2）

> T-0132 设计文档 · 2026-08-07 · candidate-only（不落地）
> 关联：D-01 §5（轮次协议）/ D-02 M4（抽查复算失败升级）

## 1. 威胁模型

| 威胁 | 描述 | 触发路径 |
|---|---|---|
| D1 状态损坏锁死 | state/gates/task_graph 三文件不一致或损坏 → validate_state fail-closed → 所有写入被 hook 拒绝 → 项目无法继续任何任务 | 半同步写入、异常中断、人为误改 |
| D2 连续性漂移锁死 | project_continuity.yaml 源哈希与源文件不符 → 校验器 fail-closed；render_handoff 也拒绝工作（本任务执行中实测：gates.yaml 每次变更都会触发，需 --repair 或先修再生成） | 任何治理文件变更后未重生成连续性 |
| D3 自治中断残留 | 自治执行中断（进程被杀/网络断）→ rounds 日志悬空、evidence 半写 → 恢复后无法判定状态 | checkpoint 心跳缺失 |
| D4 修复器自锁 | L1 修复器本身依赖状态文件可读，若文件已损坏到不可解析 → 修复器不可用 | 物理损坏、编码损坏 |

## 2. 三级 break-glass 恢复路径

### L1 项目内修复器（状态可读但损坏）

**适用**：D1/D2 且治理文件仍可解析（YAML 可 load）。

| 工具 | 现状（已实测验证） | 增强设计 |
|---|---|---|
| `validate_state.py --repair` | ✅ 本任务已 3 次实际使用：自动修复 continuity 源哈希漂移（SOURCE_DRIFT fixed=N） | 不变；补充"修复前自动快照"（见 §3） |
| `repair_continuity`（T-0049/T-0111） | ✅ 存在，guard-events 有 repair 事件记录 | 不变 |
| `continuity_producer.render_handoff` | ✅ 存在（本任务已用） | 注意顺序依赖：必须先 repair 再 render（本次实测）——写入文档 |
| `close_session.py` | ✅ 会话收尾 | 不变 |

**L1 判定**：`validate_state.py` 报错但 YAML 可解析 → L1 可用。
**L1 失败条件**：YAML 解析失败 / --repair 后错误不减 → 升级 L2。

### L2 治理外快照回滚（状态损坏到 L1 不可修）

**适用**：D1 严重损坏（不可解析）、D4 修复器自锁、--repair 无效。

**流程（四步，顺序强制）**：

```
① 快照先行 ── 当前完整状态归档（不删除任何东西）：
   · git commit 或 stash 当前工作区（含损坏文件——留原始副本）
   · .ai/evidence/<task>/recovery/snapshot-<ts>/ 复制 state/gates/task_graph/HANDOFF/continuity 原样
② 回滚 ── git 回退到最近健康提交（git log 定位：validate_state 通过的最近 commit）
③ 范围恢复 ── 仅恢复治理文件到健康版本：
   · 恢复 .ai/state.yaml / gates.yaml / task_graph.yaml / project_continuity.yaml / HANDOFF.md
   · 不动 evidence 历史、不动代码产物、不动 guard-events（append-only）
   · 证据目录中新增的 evidence 文件保留（它们是真产物，不属于损坏物）
④ 留痕 ── recovery/snapshot 目录写 RECOVERY.md：时间戳、回滚目标 commit、
   恢复范围、保留内容、被回滚的登记（如 T-0132 登记被回滚则任务标记需重登记）
```

**回滚三原则（任务卡硬约束）**：
1. **快照先行**：任何删除/覆盖前，先归档原样副本
2. **范围分级**：只动"损坏的治理文件"，evidence 历史与代码产物永不因回滚丢失
3. **动作留痕**：回滚动作记录（RECOVERY.md + guard-events 追加 recovery 事件）

**D1 回滚后的衔接**：若回滚撤销了某个任务登记，任务卡保持原样但标记
`needs_re-registration`，恢复路径中显式列出——不静默丢失任务意图。

### L3 手工接管（治理完全不可用）

**适用**：L2 失败（git 历史也损坏）或用户/开发者需要直接干预。

```
① 切 loop_mode = MANUAL（直接编辑 state.yaml loop_mode 字段——这是唯一
   允许在损坏态直接编辑的字段；或通过 zcode config 关闭 hook 执行）
② 用户/开发者直接修复文件（无 hook 约束，但保留原始副本到 snapshot）
③ 修复完成后 validate_state 全绿 → 切回 FULL/DELEGATED
④ 全程留痕：MANUAL 启停记录 + 修复内容 + 证据快照
```

**安全边界**：L3 是最后手段；规则层（AGENTS.md、forbidden 语义）在 L3 下
也要求用户显式 gate 才能改（"规则层只能用户改"不因 L3 豁免）。

## 3. 锁死预防（前置于恢复）

| 机制 | 设计 | 对治 |
|---|---|---|
| 状态原子写 | 治理文件写入走事务式（临时文件+rename，与 executor 原子写对齐）；多文件同步（state/task_graph/gates）按固定顺序 + 每文件写后校验 | D1 半写 |
| 三文件一致性检测 | validate_state 已有（`governor_lib.governance_invariant_errors` 对 state/task_graph/gates 交叉校验；本项目执行中实测抓到过三态不一致）；扩展为登记后自动校验（登记动作完成即跑） | D1 登记漂移 |
| checkpoint 心跳 | 自治执行中每个 checkpoint（每动作/每轮）执行：validate_state + rounds 日志闭合检查；任一失败 → **fail-stop 暂停**（自动冻结当前动作）→ 走 L1（可修）或 L2（不可修）→ 恢复后从 checkpoint 继续 | D3 中断残留 |
| 治理文件变更后自动重生成 | gates/state/task_graph 变更 → 自动 repair continuity + render handoff（本次实测的"每次变更都要手工 repair"是高频 D2 触发源，应自动化） | D2 漂移 |
| 修复器只读优先 | L1 工具一律先 dry-run 展示将改内容，--force 才落盘 | D4 修复器二次破坏 |

## 4. 恢复演练（可用性被证明）

**原则**：锁死恢复路径必须定期演练，演练通过才允许自治执行（与"演练通过→授权
自治"的信任建立一致）。

| 演练场景 | 注入方式 | 通过标准 |
|---|---|---|
| E1 状态漂移 | 人为改 task_graph 中 current task 状态 | `--repair` 或 L1 流程恢复 + validate 全绿 |
| E2 连续性漂移 | 人为改 gates.yaml 一行（不更新 continuity） | L1 自动/手动修复 + render handoff 成功 |
| E3 YAML 损坏 | 人为破坏 state.yaml 语法 | L1 失败确认 → L2 快照回滚恢复 → 证据保留断言（原证据仍在） |
| E4 自治中断残留 | 模拟 rounds 日志悬空 | 心跳检测发现 → fail-stop → 恢复后从 checkpoint 续跑 |
| E5 回滚不无脑删 | E3 后检查 | 回滚后：快照存在、evidence 历史完整、guard-events 无删除、RECOVERY.md 存在 |

演练频率建议：每次自治委托链开始前跑 E1/E2（轻量）；每季度全量 E1~E5。

## 5. 设计约束回顾（对应任务卡 AC-03）

| 任务卡要求 | 设计落点 |
|---|---|
| 三级 break-glass 恢复 | §2 L1/L2/L3（含现有工具盘点：--repair/repair_continuity/render_handoff 均实测可用） |
| 回滚三原则（快照先行/范围分级/动作留痕） | §2 L2 四步流程 + RECOVERY.md + guard-events 事件 |
| checkpoint 心跳 | §3（fail-stop + 从 checkpoint 续跑） |
| 恢复演练 | §4（E1~E5 + 演练通过才授权自治） |

## 6. 残余风险（诚实标注）

| 风险 | 等级 | 说明 |
|---|---|---|
| L2 回滚目标选择错误（回滚过头丢失有效登记） | MEDIUM | 快照 + RECOVERY.md + 回滚范围分级缓解；回滚后需 validate + 人工抽查登记完整性 |
| L3 手工接管后规则层被误改 | LOW | 规则层变更仍需用户 gate（不豁免） |
| 演练覆盖不足（未演练的损坏形态） | MEDIUM | 演练场景随真实事故补充（incident→复盘→新增演练场景，复用 T-0097 学习回路） |
