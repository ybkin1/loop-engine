# 批 1 批次证据 —— 纯文档（设计-1 / 设计-2 / 设计-4）

> 任务：T-0104 | 日期：2026-08-02 | 落地依据：D-03 §1.3 / §2.3 / §4.3
> 批次性质：提示词/模板/文档加节，零代码改动。

## 改了什么（7 个文件）

| 路径 | 改动点 | 设计编号 |
|---|---|---|
| `skills/loop-governance/templates/task-card.md` | +3 个必填节：信息完整度声明 + 象限判定（D-03 §2.3.1 候选文本原样）、相关经验与不熟悉处（§5.3.1）、盲点清单（§1.3.1）。节序：基本信息 → 信息完整度 → 用户可见目标 → 相关经验 → 范围与边界 → 盲点清单 → 验收标准 | 1、2、5 |
| `skills/loop-governance/SKILL.md` | 启动检查清单第 7 步"盲点简报（开工前，Q3）"（§1.3.2 候选文本原样） | 1 |
| `skills/loop-governance/templates/human-review-packet.md` | 新增"六、理解确认（用户答对才算验收）"（§4.3.1 候选文本原样）；原"六、下一步"顺延为"七、下一步" | 4 |
| `agents/main-thread/SKILL.md` | 新增 §2.3 象限判定→行为选择（§2.3.2 候选文本原样）；§5.2 Gate 呈现包强制"本阶段偏离摘要"小节（§3.3.3 模板文本）；§5.3 自检规则第 7 条（needs_user_review 条数匹配）；§4 开发工程师加"deviations 数组格式合规"、主控自检加"盲点清单 ≥3 条"与"Human Review Packet 含理解确认节" | 2、3、4 |
| `agents/main-thread/CONTRACT.yaml` | fixed_stance 仅 +1 句"象限判定先行"（§2.3.3 可选）；R10/R11 原文零改动 | 2 |
| `skills/loop-governance/references/governance-lifecycle.md` | PASS 分层补充："USER_ACCEPTED 前须完成 Human Review Packet 理解确认节"（§4.3.4 可选） | 4 |
| `USER-PROMPTS.md` | 新增"关于'AI 会先声明信息完整度再决定是否提问'"用户说明（§2.3.3 可选） | 2 |

候选文本均按 D-03"直接可复制"要求原样落地，未改写语义、未新增机制。

## 测试结果

- 新增 `tests/test_t0104_templates.py`（11 项）：三节存在且顺序正确、第 7 步、
  理解确认节 + "七、下一步"（且无残留"六、下一步"）、R10/R11 原文逐字断言、
  "象限判定先行"存在、lifecycle 前置说明、USER-PROMPTS 说明节。**全部通过**。
- 全量回归见批次总览（无新增失败）。

## 约束自查（git diff）

- `git diff --stat -- hooks/` → 空（hooks/ 零改动）
- `git diff agents/main-thread/CONTRACT.yaml` → 仅 +1 行（R10/R11 行前缀为空格，未改动）
- `git diff --stat -- loop_core/` 本批无涉及（批 1 纯文档）

## 回退

删除对应新增节/步骤即完全回退（纯文档，无状态迁移，D-03 §1.4/§2.4/§4.4）。
