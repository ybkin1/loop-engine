# T-0052 全面治理修复 — 最终证据

2026-07-27

## 最终测试结果

```text
2397 passed, 61 skipped, 16 xfailed, 1 xpassed, 0 failed, 13 warnings
```

## 最终状态校验

```text
[ok] state is usable
```

零 `[legacy]` 警告，零 `[error]` 错误。

## 修复清单

### 已修复（全部完成）

| # | 领域 | 修复 |
|---|------|------|
| 1 | Read 拦截 | `hooks.json` + Read → PreToolUse matcher + 无任务时仅治理元数据可读 |
| 2 | Bash 探索阻断 | 无任务时 find/grep/git status/ls 全部阻断 |
| 3 | Bootstrap 保护 | Agent/Skill/Task 豁免前置，无任务时可创建提案 |
| 4 | Recovery 通道 | `GOVERNANCE_RECOVERY` recovery_mode + 仅治理骨架可写 |
| 5 | 新旧统一 | Runtime Controller 与 legacy hook Read/Bash/Agent 语义一致 |
| 6 | User Gate | `USER_GATE_PHASES` + EnforcementHub 判定 + S1/S6 需要用户审批 |
| 7 | 委派合同 | `DelegationRequest` 默认只读单层 + 禁止 developer→reviewer |
| 8 | 能力探针 | `AgentCapabilityProbe` 保守返回 NOT_VERIFIED |
| 9 | Legacy lab | 63/63 全部通过 |
| 10 | 任务状态 | 16 个历史任务状态字段补全 + 6 个不匹配纠正 |
| 11 | 连续性 | 源清单哈希重建 + HANDOFF 标题补全 + 审计器哈希兼容 |
| 12 | 测试 | 新增 5 个 user gate + 委派合同 + Bash 治理 + 能力探针测试 |

### 未修复（需独立 gate）

| 项 | 原因 |
|----|------|
| Transaction Registry | 需要独立 gate 创建 |
| Checkpoint 建立 | 依赖 Transaction Registry |
| ZCode Agent 递归 live-fire | 需要真实宿主环境 + 单独 gate |
