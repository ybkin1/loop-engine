# T-0147 结论包：委托链 C-002 端到端验证（legacy 3.5 闭环）

> 成果一句话：**委托链 C-002 全链路实战跑通** —— 登记→链内自治→结论包，
> 3.5 遗留项闭环，3.2 锚定修复真实运行验证。

## 成果

- **C-002 链登记成功**：覆盖 T-0144/T-0145/T-0146，锚定 G-T-0137-REQUIREMENTS
  （approved + 证据存在）
- **链内三任务全部自治完成**（免逐任务 gate）：
  - T-0144 repro_norm 规范化（22/22 测试）
  - T-0145 metrics 生成器接入（5/5 测试）
  - T-0146 词表 BLOCK/REJECTED + 拦截计数（10/10 测试）
- **3.2 锚定反例实测**：无 --gate → rc 2；不存在的 gate → rc 2（拒绝）；
  C-BAD-P 链登记后 revoked 留档（append-only 证据）

## 演示/冒烟

```bash
# 链登记与状态
python .zcode/tools/gov_delegation.py . register --chain C-002 --tasks T-0144,T-0145,T-0146 --gate G-T-0137-REQUIREMENTS
# → registered C-002 (active, gate=G-T-0137-REQUIREMENTS)

# 链内任务识别
python .zcode/tools/gov_delegation.py . check --task T-0145
# → task T-0145 is in an active delegation (rc 0)

# 反例（3.2 fail-closed）
python .zcode/tools/gov_delegation.py . register --chain C-BAD --tasks T-X
# → register requires --gate ... (rc 2)
python .zcode/tools/gov_delegation.py . register --chain C-BAD2 --tasks T-X --gate G-T-9999-REQUIREMENTS
# → register rejected: gate not found (rc 2)

# checkpoint 心跳（链内 rounds 闭合）
python .zcode/tools/rounds_heartbeat.py .
# → [heartbeat] PASS — 全部 rounds 闭合
```

## 证据路径

- 链登记/状态/反例：`.ai/gates.yaml` delegations 区块（C-002 active、
  C-BAD-P revoked 留档）+ 本会话执行记录
- 三任务证据：`.ai/evidence/T-0144/`、`T-0145/`、`T-0146/`
  （approval/execution/compile + 测试结果）
- 心跳：`rounds_heartbeat` PASS（T-0134 交付工具）
- 质量门：release check 7/7 + 全量回归 4345 passed 0 failed（修复 manifest
  后）+ 本轮 golden 演进记录（T-0110 README）

## 验收对照

| AC | 结果 |
|----|------|
| AC-01 C-002 登记（锚定 approved gate + 证据） | PASS（G-T-0137） |
| AC-02 链内任务免逐任务 gate 自治执行 | PASS（T-0144~T-0146 完成） |
| AC-03 checkpoint 心跳记录 | PASS（rounds 闭合） |
| AC-04 结论包三要素 | 本文件 |
| AC-05 3.2 锚定反例实测 | PASS（rc 2 ×2 + revoked 留档） |
| AC-06 全量回归 + 版本同步 | PASS（4345 passed 0 failed） |
| AC-07 独立审查 GO | 待批（随批量审查） |

## 3.5 闭环声明

legacy-issues-summary 3.5（委托链端到端免 gate 裁决待真实任务验证）——
**已由本批真实任务闭环**：C-002 链内 T-0144~T-0146 全自治执行，无逐任务
gate 打扰；规则层（AGENTS.md/forbidden 语义/EVIDENCE_ONLY_BOUNDARY）未
豁免；用户仅在链级批准一次。委托模式（T-0134 P4）从"基础设施就绪"升级为
"实战验证通过"。
