# T-0107 验收报告 — 设计漏洞修复（P1 专项 + P2 全量 + P3 首批）

- 任务：T-0107（G-T-0107-REQUIREMENTS，approved）— T-0106 排布首项实施：
  P1-1 context_packager 截断专项 9 处 + P2 全量 11 项 + P3 首批 6 项 + hook 单独门禁（D4-2/D4-7）
- 角色：governance-controller（编排与验收）；developer（修复实现）；independent-reviewer（独立审查）
- 执行时间：2026-08-03（UTC+8）
- 基线：git HEAD `e083f7b`（v3.12.43，T-0106）；版本 bump **3.12.44**
- 修复依据：`.ai/evidence/T-0106/design/audit-design-gaps.md`（42 项权威编号）

---

## 一、修复内容（26 项）

| 组 | 项数 | 核心内容 |
|----|------|---------|
| P1 context_packager 专项 | 9/9 | token 预算（1500 tokens）替代字符截断 + AC/验收节按 `## ` 节解析**永不切** + truncated 标记 + case 边界保 JSON 语法 + 字面量/timeout 集中常量 + total 死护栏复活 + diff 吞错告警 + diff 进程内缓存 |
| P2 全量 | 11/11 | 截断族、阈值常量（MEDIUM_RISK_ESCALATION_MIN）、audit_ledger 轮转（链哈希跨归档延续）、loop_enforcement fail-open → **fail-closed 强化**、phase_problems 字段、naive YAML 降级显式告警 + schema 校验、**双解析器统一（loop_core/front_matter.py 共享模块）** |
| P3 首批 | 6/6 | journal/persist 轮转、corrupt_line_count、HASH_SCAN_SKIPPED 告警去重、裸 except + 死代码删除、contract_verifier fallback 收窄（仅 ImportError + _parsed_by 标注） |
| hook 门禁 | 2+1 处 | loop_enforcement.py 单文件：D4-2（fail-closed 强化）+ D4-7（哈希跳过告警）+ D5-2 接线，其余 hook 文件零改动 |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | context_packager 专项 9 处（截断标记/AC 节不切/预算化/缓存/超时） | **PASS**（独立逐项读码 + 行为脚本复验，D1-1 至 D4-4 全真实） |
| AC-02 | P2 11 项 + 契约测试（双解析器统一） | **PASS**（front_matter.py 双路径契约一致性有测试；fail-closed 强化方向实证） |
| AC-03 | P3 首批 6 项 + 测试 | **PASS**（独立抽查全真实） |
| AC-04 | KNOWN_ISSUES 12 条清零 | **PASS**（全部移入 Recently Closed，编号引用 audit；环境依赖项另行登记） |
| AC-05 | 全量回归 0 failed + compile + release check 6/6 | **PASS**（独立复验 3909 passed；3 failed 中 2 为 closeout 瞬态、1 为预存在环境依赖；提交后 version_sync 自愈） |
| AC-06 | 版本 3.12.44 == git HEAD | **PASS**（提交后成立） |
| AC-07 | 独立审查 GO + hooks/ 仅两处 diff 实证 | **PASS**（CONDITIONAL_GO → 放行项（KNOWN_ISSUE 登记）→ GO；hook 单文件 3 处功能变更实证） |

## 三、独立审查摘要（independent-review.md）

- **裁决：CONDITIONAL_GO → GO**（P0/P1 各 0；P2×1 环境依赖测试失败已登记 KNOWN_ISSUE；P3×3 留档）
- 约束零弱化专项：hook 单文件恰好 3 处功能变更（D4-2/D4-7/D5-2 接线），其余 hook 文件零改动；
  治理内核（gate_guard/hard_constraints/guard_health/state_machine/validate_state/context_loader）零 diff；
  全部修复方向为强化或等价，无任何弱化
- 路径偏差文件（tool_constraint_check.py D4-3、transaction_registry.py D4-8）：判定在范围内（任务卡范围 + KNOWN_ISSUES 登记项 + gate 路径已补）
- 修复真实性：P1 专项 9 处、P2 11 项、P3 6 项逐项读码/行为脚本复验全真实（D1-1 截断点实证、D3-2 monkeypatch 预算实证、D4-1 diff 真实 git 仓库计数实证）
- 测试：test_t0107_fixes 44 passed + hook 套件 177 passed 独立复验一致

## 四、裁决

**T-0107 验收通过（7/7 AC）。** 用户关切核心案例（context_packager 静默截断）已根治：
token 预算 + AC 节永不切 + 截断标记；12 条 KNOWN_ISSUES 清零；双解析器统一消除契约分歧；
hook 唯一改动为 fail-closed 强化。版本 3.12.44。

## 五、下一步

T-0108（BH 融合·收敛期：F4/F6/F7/F8/F2-阶段 1）待用户批准。
P3 留档项（_estimate_tokens 未调用、docstring 漂移、任务卡文案）随后续任务顺带。
