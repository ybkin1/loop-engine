# 阶段 Loop 正式状态机

本文定义 Loop 工程治理的阶段级状态机。它是角色间交接协议的上层——角色 Loop 在阶段内部运行，阶段 Loop 在角色之上编排。

---

## 1. 阶段状态枚举

```
PHASE_START
    → ENTRY_CHECK
        → [入口条件不满足] → BLOCKED_AT_ENTRY（升级给用户）
        → [入口条件满足] → ROLE_EXECUTION

ROLE_EXECUTION
    → [所有角色完成其 Loop] → INTEGRATION
    → [角色产出存在冲突] → ROLE_EXECUTION（打回相关角色返工）

INTEGRATION
    → [集成检查通过] → QUALITY_CHECK
    → [集成检查失败] → ROLE_EXECUTION（打回相关角色，附冲突详情）

QUALITY_CHECK
    → [质量门全部 PASS] → HUMAN_REVIEW_PACKET
    → [质量门存在 BLOCKED] → ROLE_EXECUTION（打回对应角色修复）

HUMAN_REVIEW_PACKET
    → [包已组装] → WAITING_FOR_HUMAN_REVIEW

WAITING_FOR_HUMAN_REVIEW（阻塞态——gate_guard hook 阻断一切写入）
    → [用户决定 APPROVE_NEXT_PHASE] → APPROVED_NEXT_PHASE（阶段结束）
    → [用户决定 RETURN_FOR_REWORK] → 回到 ROLE_EXECUTION
    → [用户决定 CHANGE_DIRECTION] → CHANGE_DIRECTION（阶段终止）
```

---

## 2. 状态定义

| 状态 | 含义 | 停留限制 |
|------|------|---------|
| PHASE_START | 阶段已被主控启动 | 瞬时，不得等待 |
| ENTRY_CHECK | 验证入口条件 | 最多 1 轮 |
| BLOCKED_AT_ENTRY | 入口条件不满足 | 升级用户后解除 |
| ROLE_EXECUTION | 角色执行各自 Loop | 可多轮（返工） |
| INTEGRATION | 集成检查 | 最多 1 轮 |
| QUALITY_CHECK | 质量门运行 | 最多 1 轮 |
| HUMAN_REVIEW_PACKET | 组装人工评审包 | 瞬时 |
| WAITING_FOR_HUMAN_REVIEW | 等待用户决策 | **无限期阻塞** |
| APPROVED_NEXT_PHASE | 阶段完成 | 瞬时，进入下一阶段 |
| CHANGE_DIRECTION | 方向变更 | 归档终止 |

---

## 3. 关键约束

1. **状态流转方向不可逆** — 除 RETURN_FOR_REWORK 可回到 ROLE_EXECUTION 外，任何状态不能跳回更早的状态
2. **WAITING_FOR_HUMAN_REVIEW 后只有用户能驱动** — 系统不得自动推进
3. **返工必须走完整链路** — RETURN_FOR_REWORK 后必须重新走 INTEGRATION → QUALITY_CHECK → HUMAN_REVIEW_PACKET
4. **gate_guard 物理阻断** — 在 WAITING_FOR_HUMAN_REVIEW 期间，exit 2 阻断一切写入

---

## 4. 12 阶段定义

### S0-init（初始化）
- **目的**: 项目治理环境初始化
- **主导角色**: R11（主控编排）
- **交付物**: .ai/state.yaml, .ai/gates.yaml, .ai/task_graph.yaml
- **入口条件**: 用户指令创建项目
- **放行条件**: 治理文件完整可用

### S1-requirements（需求分析）
- **目的**: 从模糊需求中提炼清晰的产品定义
- **主导角色**: R01（产品经理）
- **参与角色**: R02（项目经理）
- **交付物**: product-requirements.md, acceptance-criteria.md, priority-matrix.md
- **入口条件**: S0 APPROVED
- **放行条件**: 每条需求有唯一ID + 验收标准 + 优先级排序有依据

### S2-architecture（架构设计）
- **目的**: 设计系统整体架构
- **主导角色**: R04（系统架构师）
- **参与角色**: R01（需求澄清）, R08（安全边界）
- **交付物**: architecture-design.md（14项）, module-boundaries.md, interface-contracts.md, adr-records.md
- **入口条件**: S1 APPROVED + 需求基线化
- **放行条件**: 14项架构交付物完整 + 无循环依赖 + 安全边界已定义

### S3-interface（详细设计）
- **目的**: 将架构分解到函数级别
- **主导角色**: R05（模块架构师）
- **参与角色**: R04（架构一致性审查）
- **交付物**: detailed-design.md, function-specs.md
- **入口条件**: S2 APPROVED
- **放行条件**: 每个函数有签名+前置+后置+异常

### S4-implementation（编码）
- **目的**: 依据设计实现代码
- **主导角色**: R06（开发工程师）
- **参与角色**: R05（接口一致性检查）
- **交付物**: 源代码, 测试代码, implementation_notes.md
- **入口条件**: S3 APPROVED
- **放行条件**: lint=0 + typecheck=0 + 单元测试全部通过 + 独立评审PASS

### S5-quality（质量验证）
- **目的**: 全面质量门禁
- **主导角色**: R07（质量工程师）
- **参与角色**: R06（修复）, R08（安全审查）
- **交付物**: quality-report.md, security-report.md, test-coverage.md
- **入口条件**: S4 APPROVED
- **放行条件**: P0=0, P1=0 + 覆盖率≥80% + HIGH=0, CRITICAL=0

### S6-delivery（交付）
- **目的**: 交付物完整性验证 + 用户验收
- **主导角色**: R03（交付经理）
- **参与角色**: R10（部署）, R08（最终安全审计）
- **交付物**: delivery-checklist.md, release-notes.md, rollback-plan.md
- **入口条件**: S5 APPROVED
- **放行条件**: 交付物100%可验证 + 回滚方案就绪 + **用户明确批准**

### S7-integration（集成）
- **目的**: 多模块集成验证
- **主导角色**: R06（开发工程师）
- **参与角色**: R05（接口覆盖）, R07（集成测试）
- **交付物**: integration-test-report.md
- **入口条件**: S6 APPROVED
- **放行条件**: 所有集成测试通过 + 每个接口至少一个集成测试覆盖

### S8-functional-test（功能测试）
- **目的**: 从用户视角验证功能满足度
- **主导角色**: R07（质量工程师）
- **参与角色**: R01（需求满足度确认）
- **交付物**: functional-test-report.md
- **入口条件**: S7 APPROVED
- **放行条件**: 每个功能项有测试结果 + 无CRITICAL/HIGH功能缺陷

### S9-fix-optimize（修改优化）
- **目的**: 修复缺陷、优化性能
- **主导角色**: R06（开发工程师）
- **参与角色**: R09（审查修改）, R07（回归测试）
- **交付物**: rework-tracker.md, review-report.md
- **入口条件**: S8 APPROVED
- **放行条件**: 所有HIGH/CRITICAL已修复 + 回归测试通过 + 评审PASS

### S10-performance（压力测试）
- **目的**: 验证性能和稳定性
- **主导角色**: R07（质量工程师）
- **参与角色**: R10（环境准备）, R04（性能分析）
- **交付物**: stress-test-report.md, environment-spec.md
- **入口条件**: S9 APPROVED
- **放行条件**: 满足QPS/延迟指标 + 无内存泄漏 + 架构师确认

### S11-maintenance（维护）
- **目的**: 持续维护——监控、修复、迭代
- **主导角色**: R10（发布运维）
- **参与角色**: R08（持续安全）, R06（按需修复）
- **交付物**: monitoring-report.md, security-scan-report.md, incident-log.md
- **入口条件**: S10 APPROVED
- **放行条件**: 无终点——持续运行直到用户决定结束

---

## 5. 阶段团队总表

| 阶段 | 编号 | 主导角色 | 参与角色 |
|------|------|---------|---------|
| 初始化 | S0 | R11 | — |
| 需求分析 | S1 | R01 | R02 |
| 架构设计 | S2 | R04 | R01, R08 |
| 详细设计 | S3 | R05 | R04 |
| 编码 | S4 | R06 | R05 |
| 质量验证 | S5 | R07 | R06, R08 |
| 交付 | S6 | R03 | R10, R08 |
| 集成 | S7 | R06 | R05, R07 |
| 功能测试 | S8 | R07 | R01 |
| 修改优化 | S9 | R06 | R09, R07 |
| 压力测试 | S10 | R07 | R10, R04 |
| 维护 | S11 | R10 | R08, R06 |

---

## 6. Loop 模式与阶段裁剪

| 模式 | 阶段范围 | 适用场景 |
|------|---------|---------|
| FULL | S0→S11 全部 | 大型项目、安全敏感、多模块 |
| STANDARD | S0→S6（跳过S7-S11） | 中型项目、常规交付 |
| LITE | S1→S4→S6（跳过架构/质量） | 小型工具、原型 |
| HOTFIX | S4→S6（直接修复+交付） | 紧急修复 |

---

## 7. 状态流转图

```
PHASE_START → ENTRY_CHECK → [PASS] → ROLE_EXECUTION → INTEGRATION → QUALITY_CHECK
                                                                          ↓
                                                                HUMAN_REVIEW_PACKET
                                                                          ↓
                                                              WAITING_FOR_HUMAN_REVIEW
                                                                    ↙   ↓    ↘
                              APPROVED_NEXT_PHASE    RETURN_FOR_REWORK    CHANGE_DIRECTION
                                   ↓                       ↓                    ↓
                              下一阶段                ROLE_EXECUTION         归档终止
                              PHASE_START              （重入）
```
