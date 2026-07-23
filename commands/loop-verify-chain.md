---
description: 验证 Loop 工程证据链完整性——检查 hash 链是否闭合
argument-hint: "[--phase NN] [--strict]"
allowed-tools: [Bash, Read]
---

验证从需求到当前阶段的证据链是否完整闭合。

## 用法

```
/loop-verify-chain                 # 验证全部已定义节点
/loop-verify-chain --phase PHASE-05  # 仅验证到指定阶段
/loop-verify-chain --strict        # 严格模式——缺 required 节点 = BLOCKED
```

## 输出

- PASS → 所有已声明的 input_hashes 与上游文件实际 SHA256 一致
- BLOCKED → 存在 HASH_MISMATCH（证据 stale）或 MISSING（链断裂）

示例：
```
[evidence_chain] 发现 1 个问题:
  - [HASH_MISMATCH] quality_report 声明的 source_code=sha256:abc，实际 SHA256=sha256:def——证据 stale
[evidence_chain] BLOCKED
```
