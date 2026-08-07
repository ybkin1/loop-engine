# T-0151: Roadmap Backlog 评估与落地记录

> 交付物：T-0151（AC-03/AC-04）
> 日期：2026-08-07
> 来源：docs/designs/loop-v4-consolidated-roadmap.md §2.3 backlog 项

## 1. 落地项（本次完成）

### 1.1 Test strategy 金字塔（roadmap T-0108 建议）
- **落地**：`skills/loop-governance/templates/testing/test-strategy.md` 新增
  §4.5 测试金字塔约束（70/20/10，±10% 容差 + 偏离理由必填）
- **检查点**：release-checklist 对应（单元 ≥60% / E2E ≤15%）
- 对应 backlog：test strategy enforcement（pyramid 70/20/10）

### 1.2 Debt register / bug caps（roadmap T-0104 建议）
- **落地**：`.ai/KNOWN_ISSUES.md` 新增 `## Debt Register` 结构化账本
  （P0~P3 分级 + 来源 + 处理列，DR-001~DR-005 初始登记）
- 对应 backlog：bug caps / defect tracking（debt register）

## 2. 评估项（候选，交用户裁决）

### 2.1 Tech-writer 角色（roadmap T-0105）
- **可行性**：高 —— 现有 4 角色（architect/developer/quality/security）已
  覆盖技术产出；文档/报告生成（runbook/docs-as-code）可由独立角色承担
- **工作量**：S（新角色 SKILL + CONTRACT + references + 挑战认证）
- **建议**：可立项（P3），但不紧急 —— 当前 main-thread 已能产出交付文档

### 2.2 SRE 角色（roadmap T-0106）
- **可行性**：中 —— 需要部署通道/运行时环境支撑（当前引擎无真实部署目标）；
  T-0143 已补发布/稳定性检查点（release-engineer 承担大部分 SRE 职责）
- **建议**：推迟 —— 无部署通道时角色空转；已由 release-engineer +
  稳定性模板（T-0138）覆盖

### 2.3 Threat-modeling / DAST / SCA 增强（roadmap T-0107）
- **可行性**：中 —— security-engineer 已有 SAST/SCA 扫描（run_security_scan）；
  缺 STRIDE 威胁建模门禁与 DAST 动态扫描
- **工作量**：M（STRIDE 模板 + DAST 工具接入 + 门禁检查点）
- **建议**：可立项（P3），随真实项目安全需求触发

## 3. Backlog 状态表

| Backlog 项 | 状态 | 理由 |
|------------|------|------|
| Bug caps / debt register（T-0104） | ✅ 落地 | KNOWN_ISSUES Debt Register |
| Test strategy 金字塔（T-0108） | ✅ 落地 | test-strategy §4.5 |
| Tech-writer 角色（T-0105） | ⏸ 候选 | 可立项 P3，不紧急 |
| SRE 角色（T-0106） | ⏸ 推迟 | 无部署通道，release-engineer 已覆盖 |
| Threat-modeling/DAST/SCA（T-0107） | ⏸ 候选 | 随真实项目安全需求触发 |

## 4. 边界确认

- 未新建角色（tech-writer/SRE 仅评估，落地需用户独立 gate）
- hooks/ 零改动、内核零触碰
- 版本保持 3.12.67
