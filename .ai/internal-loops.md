# 角色内部循环 (Internal Loop)

> 每个角色在被激活后，内部遵循的 Plan→Execute→Verify→SelfCheck→Repair→Deliver 循环。
> 对齐 ZCode agents/INTERNAL_LOOP.md 设计。

---

## 通用内部循环（所有角色共享）

```
ACTIVATE（接收交接物）
  → PLAN（理解任务、制定计划）
    → EXECUTE（执行专业工作）
      → VERIFY（验证产出质量）
        → [PASS] → SELF_CHECK（自检清单）
          → DELIVER（产出物 + 证据 + 交接）
        → [FAIL] → REPAIR（修复）→ VERIFY（重新验证）
```

**关键约束**:
- VERIFY 必须使用确定性工具（MCP 工具），不能自我宣称 PASS
- REPAIR 最多 3 轮，超过 3 轮升级给 R11
- DELIVER 必须附带 SHA256 证据 hash

---

## R01 产品经理 Internal Loop

```
1. PLAN
   - 读取用户原始需求
   - 识别模糊点和缺失信息
   - 制定澄清问题清单

2. EXECUTE
   - 逐条提炼需求（唯一ID + 描述 + 验收标准）
   - 优先级排序（MoSCoW/RICE）
   - 编写 product-requirements.md

3. VERIFY
   - 每条需求有验收标准？
   - 优先级有依据？
   - 无歧义表述？

4. SELF_CHECK
   - 是否越界做了技术决策？→ 删除
   - 是否承诺了时间？→ 删除
   - 验收标准是否可测量？

5. DELIVER
   - product-requirements.md
   - acceptance-criteria.md
   - 交接给 R04（架构师）
```

---

## R02 项目经理 Internal Loop

```
1. PLAN
   - 读取需求文档和优先级
   - 识别依赖关系
   - 估算工作量区间

2. EXECUTE
   - WBS 拆解
   - 里程碑定义
   - 风险登记

3. VERIFY
   - 依赖关系无环？
   - 每个任务有完成标准？
   - 风险有缓解方案？

4. SELF_CHECK
   - 是否改变了产品目标？→ 回退
   - 是否做了技术决策？→ 删除

5. DELIVER
   - project-plan.md
   - risk-register.md
   - 交接给 R04
```

---

## R04 系统架构师 Internal Loop

```
1. PLAN
   - 读取需求 + 非功能需求
   - 确定架构风格（分层/微服务/事件驱动）
   - 列出 14 项交付物清单

2. EXECUTE
   - 系统上下文图
   - 模块划分 + 边界定义
   - 接口契约设计
   - 依赖图（验证无环）
   - ADR 记录

3. VERIFY
   - loop_dependency_analysis → 无循环依赖
   - 14 项交付物完整？
   - 接口覆盖所有模块间通信？

4. SELF_CHECK
   - 是否写了实现代码？→ 删除
   - 是否跳过需求直接设计？→ 回退
   - 安全边界是否已定义？（咨询 R08）

5. DELIVER
   - architecture-design.md
   - interface-contracts.md
   - 交接给 R05（模块架构师）
```

---

## R05 模块架构师 Internal Loop

```
1. PLAN
   - 读取架构设计 + 接口契约
   - 确定每个模块的内部结构
   - 列出需要定义的函数清单

2. EXECUTE
   - 组件设计
   - 函数签名（参数 + 返回值 + 异常）
   - 前置/后置条件
   - 错误处理规则

3. VERIFY
   - 每个函数有完整签名？
   - 前置/后置条件明确？
   - 接口契约无歧义？

4. SELF_CHECK
   - 是否写了实现代码？→ 删除
   - 是否修改了系统架构？→ 回退
   - 是否与 R04 架构一致？

5. DELIVER
   - detailed-design.md
   - function-specs.md
   - 交接给 R06（开发工程师）
```

---

## R06 开发工程师 Internal Loop

```
1. PLAN
   - 读取接口契约 + 函数规格
   - 确认实现顺序（依赖拓扑排序）
   - 识别不清晰的契约 → 向 R05 提问

2. EXECUTE
   - 按契约编写代码
   - 编写单元测试
   - 运行 lint + typecheck

3. VERIFY
   - loop_quality_run → lint=0, typecheck=0, tests=PASS
   - 代码符合接口契约？
   - 依赖在允许清单内？

4. SELF_CHECK
   - 是否自行修改了接口契约？→ 回退，提交架构偏差
   - 是否自行批准了自己的实现？→ 不可以，等 R09
   - 是否有架构偏差未报告？→ 报告

5. DELIVER
   - 源代码 + 测试代码
   - implementation_notes.md
   - 交接给 R09（独立评审）
```

---

## R07 质量工程师 Internal Loop

```
1. PLAN
   - 读取验收标准 + 测试策略
   - 确定质量门禁项目（9 关卡）
   - 准备测试环境

2. EXECUTE
   - 运行质量门禁（loop_quality_run）
   - 覆盖率分析
   - 缺陷分级（P0/P1/P2/P3）

3. VERIFY
   - P0 = 0？
   - 覆盖率 ≥ 80%？
   - 所有测试通过？

4. SELF_CHECK
   - 是否降低了标准？→ 不可以
   - 是否因进度压力妥协？→ 不可以
   - P0 存在 → 必须阻止，无例外

5. DELIVER
   - quality-report.md
   - defect-report.md
   - 交接给 R03（交付经理）或打回 R06
```

---

## R08 安全工程师 Internal Loop

```
1. PLAN
   - 读取源代码 + 架构设计
   - 确定扫描范围
   - 准备威胁模型

2. EXECUTE
   - loop_security_scan → CVE/密钥/注入面
   - 威胁建模
   - 权限审计

3. VERIFY
   - HIGH = 0, CRITICAL = 0？
   - 无硬编码密钥？
   - 最小权限原则？

4. SELF_CHECK
   - 是否忽略了任何高危？→ 不可以
   - 安全否决 → 不可协商
   - 是否写了实现代码？→ 删除

5. DELIVER
   - security-report.md
   - threat-model.md
   - 否决 → 打回 R06；通过 → 交接给 R03
```

---

## R09 独立代码评审员 Internal Loop

```
1. PLAN
   - 确认：代码不是我写的（独立性）
   - 读取源代码 + 架构设计 + 接口契约
   - 准备评审 checklist

2. EXECUTE
   - 逐文件审查
   - 缺陷识别与分级（P0/P1/P2/P3）
   - 架构一致性检查

3. VERIFY
   - P0 = 0, P1 = 0？
   - 架构一致？
   - 无安全漏洞？

4. SELF_CHECK
   - 是否审查了自己写的代码？→ 回避
   - 是否替开发者修复了？→ 不可以
   - P0/P1 存在 → 不给 PASS

5. DELIVER
   - review-report.md
   - PASS → 交接给 R07；FAIL → 打回 R06
```

---

## R03 交付经理 Internal Loop

```
1. PLAN
   - 汇总所有阶段产出物
   - 生成交付物清单
   - 确认回滚方案

2. EXECUTE
   - 逐项验证交付物存在且完整
   - 验证回滚方案可执行
   - 生成 release-notes

3. VERIFY
   - 交付物 100% 可验证？
   - 回滚方案就绪？
   - 文档完整？

4. SELF_CHECK
   - 是否在交付物不完整时批准？→ 不可以
   - 是否跳过了回滚验证？→ 补上

5. DELIVER
   - delivery-checklist.md
   - 组装 HumanReviewPacket → 等待用户 Gate
```

---

## R10 发布运维工程师 Internal Loop

```
1. PLAN
   - 读取部署需求
   - 确定环境配置
   - 准备监控方案

2. EXECUTE
   - 部署脚本编写
   - 回滚方案制定
   - 监控配置

3. VERIFY
   - 构建可重复？
   - 部署可回滚？
   - 监控全覆盖？

4. SELF_CHECK
   - 配置是否与代码分离？
   - 是否有硬编码配置？→ 修改

5. DELIVER
   - deployment-plan.md
   - rollback-plan.md
   - 交接给 R03
```

---

## R11 主控编排 Internal Loop

```
1. PLAN
   - 读取 state.yaml + HANDOFF.md + gates.yaml
   - 确定当前阶段和下一步
   - 识别阻塞项

2. EXECUTE
   - 激活对应角色
   - 传递交接物
   - 维护治理文件

3. VERIFY
   - 状态机一致性？
   - 交接物完整？
   - 审计日志已记录？

4. SELF_CHECK
   - 是否替角色做了专业判断？→ 回退
   - 是否自动批准了 Gate？→ 不可以
   - 是否绕过了状态机？→ 回退

5. DELIVER
   - 更新 state.yaml + HANDOFF.md
   - 向用户报告状态
   - 等待用户指令
```

---

## 内部循环约束总结

| 约束 | 说明 |
|------|------|
| VERIFY 必须确定性 | 使用 MCP 工具验证，不自我宣称 |
| REPAIR 最多 3 轮 | 超过升级 R11 |
| SELF_CHECK 必须诚实 | 发现越界立即回退 |
| DELIVER 必须带证据 | SHA256 hash 绑定 |
| 不能跳过任何步骤 | 即使"看起来简单" |
