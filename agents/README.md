# Loop 工程角色体系

## 目录

```
agents/
├── README.md                        # 本文件
│
├── main-thread/                     # 主控会话（编排者、记录官）
│   └── SKILL.md
│
├── product-manager/                 # 产品经理
│   └── SKILL.md
│
├── project-manager/                 # 项目经理
│   └── SKILL.md
│
├── system-architect/                # 系统架构师
│   ├── SKILL.md
│   └── references/
│       └── architecture-checklist.md
│
├── module-architect/                # 模块架构师
│   ├── SKILL.md
│   └── references/
│       └── interface-contract-spec.md
│
├── developer/                       # 开发工程师
│   ├── SKILL.md
│   └── references/
│       └── coding-standards.md
│
├── quality-engineer/                # 质量工程师（已完成原型）
│   ├── SKILL.md
│   ├── references/
│   │   └── quality-standards.md
│   └── scripts/
│       ├── check_thresholds.py
│       └── run_quality_gates.py
│
├── security-engineer/               # 安全工程师
│   ├── SKILL.md
│   └── references/
│       └── security-checklist.md
│
├── independent-reviewer/            # 独立代码评审员
│   ├── SKILL.md
│   └── references/
│       └── review-checklist.md
│
├── delivery-manager/                # 交付经理
│   └── SKILL.md
│
├── release-engineer/                # 发布/运维工程师
│   ├── SKILL.md
│   └── references/
│       └── deployment-checklist.md
│
└── references/                      # 跨角色协议
    ├── role-conflict-protocol.md    # 角色冲突处理协议
    ├── handoff-standard.md          # 角色间交接协议标准
    └── phase-loop-state-machine.md  # 阶段 Loop 正式状态机（12 阶段定义）
```

## 角色关系

```
        产品经理（需求）
             ↓
        项目经理（计划）
             ↓
    系统架构师 → 模块架构师
                      ↓
                  开发工程师
                      ↓
    ┌────────┬────────┼────────┬────────┐
   质量工程师  安全工程师  独立评审员  发布工程师
    └────────┴────────┼────────┴────────┘
                      ↓
                  交付经理
                      ↓
                 用户 Gate
```

每个箭头 = 一次交接验收。下游有权打回上游。冲突时走 `references/role-conflict-protocol.md`。

## 每个角色的合同标准

12 字段：
1. 角色身份 2. 固定立场 3. 职责范围 4. 明确禁止 5. 输入资料 6. 输出产物
7. 质量标准 8. 可否决事项 9. 上游验收 10. 下游交接 11. 冲突处理 12. 证据要求

## 运行方式（v3.6 宿主编排模式）

ZCode 子代理不具备 Agent 工具（live-fire 已证实），因此采用宿主编排：

1. 用户会话拉起 main-thread Agent → 产出 SubagentManifest（编排计划）
2. 宿主（用户会话）使用 `loop_core/dispatcher.py` 按清单并行调用角色 Agent
3. 每个角色 Agent 加载自己的 SKILL.md + references + scripts，**不能**访问其他角色的运行上下文
4. main-thread 收到聚合结果后验证产出并呈现 gate
