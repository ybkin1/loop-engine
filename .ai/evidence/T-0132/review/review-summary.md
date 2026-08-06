# T-0132 独立审查报告（最终版）

> 审查方式：独立 subagent（general-purpose）两轮审查（首轮 + 修复复核）· 2026-08-07
> 最终结论：**GO**

## 审查范围

- D-01-three-layer-model.md / D-02-anti-fabrication.md / D-03-anti-deadlock.md /
  decision-packet.md 四份设计文档 + 任务卡 T-0132.md
- 对照真实代码接口：loop_core/evals.py、subagent_manifest.py、guard_health.py、
  observability.py、router.py、verdicts.py、agents/ 契约、.zcode/tools/

## 硬约束逐条核验（用户指定）

| 项 | 首轮 | 复核 | 要点 |
|---|---|---|---|
| A1 机器可复算 | PASS | ✅ | M1 闭环 + repro_hash 规范化边界已定义 |
| A2 检验者不见预期 | PASS | ✅ | M2 prompt 规范 + input_files 机器校验 |
| A3 防倒填 | PASS | ✅ | M3 哈希先行 + jsonl 物理顺序 + git_commit 锚 |
| A4 抽查复算 | PASS | ✅ | M4 CHECK_RECOMPUTE + 任务粒度统计口径 |
| A5 verdict 引用证据 | PASS | ✅ | M5 无引用=FAIL，evidence_ref 扩展显式声明 |
| B1 三级 break-glass | PASS | ✅ | L1 工具实测核实 + guard-events repair 事件佐证 |
| B2 回滚三原则 | PASS | ✅ | 快照先行/范围分级/动作留痕 |
| B3 checkpoint 心跳 | PASS | ✅ | fail-stop + 恢复续跑 |
| B4 恢复演练 | PASS | ✅ | E1~E5 可执行 |
| D2 AC-05 零改动 | PASS | ✅ | git status 确认仅 .ai/ 变更 |

## 发现与修复记录

- **P1**（首轮）：D-01 §6.2 EvalReport 落盘契约与真实接口不符
  → 已对齐真实 schema（type: eval_report / 顶层 verdict / cases 为
  EvalCaseResult.to_dict() 字段）+ 显式声明 evidence_ref 扩展（与 D-02 M5 联动）
  → 复核：逐字段比对通过，解除
- **P2 ×5**（首轮）：LoopMode 枚举位置/fail-closed 回退、eval_cases 必填字段、
  repro_hash 规范化、T-0121 归属、M4 统计口径 → 全部修复，复核通过
- **P2 ×2**（复核轮）：决策包影响面一行同步（router.py + MANUAL 回退）、
  §6.2 示例 stats 键对齐（total/passed/failed/skipped）→ 已修复

## 总结论

**GO**：防伪造五项机制闭环自洽且与 eval 栈真实接口一致；防锁死三级路径有
真实工具与事件佐证（L1 可行性论证成立）；角色分组与现有 agents/ 契约一致；
AC-05 零改动确认；两轮审查无遗留问题。
