# T-0129 验收报告

> 2026-08-07 · P2 防御演练

## AC 核验

| AC | 结果 | 证据 |
|---|---|---|
| AC-01 拒绝路径 >=6 | ✅ 6/6 | R1~R6（tests/test_defense_drills.py） |
| AC-02 E1~E5 | ✅ 5/5 | 漂移/损坏/悬空/回滚全部真实工具演练 |
| AC-03 回滚不无脑删 | ✅ | E5 四项断言（快照/evidence/guard-events/RECOVERY.md） |
| AC-04 指标语义修正 | ✅ | gate_defense 字段 + metrics-semantics.md |
| AC-05 全量回归 + bump | ✅ | 4257 passed；v3.12.64（559c65a + 9999493） |
| AC-06 独立审查 GO | ✅ | 两轮审查，P1×2 关闭 |

## 结论

**PASS（6/6 AC）**。P2 完成：防御可用性被演练证明（拒绝路径 + 锁死恢复 11/11），
心跳最小能力落地（rounds_heartbeat，完整心跳随 P4），自治授权资格达成。
