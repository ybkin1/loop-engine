# Loop Engine — 外部标准参考素材库

> 搜集方式：两个独立 Agent 并行搜索 → 第三个 Agent 交叉比对 → 确认纳入。
> 共 5 个 Agent 参与搜集（A/B 主搜 + C 交叉比对 + D 盲区补搜 + E 提示词参考 + F 验证工具）。

---

## 一、软件工程模板（9 类，共 37 个来源）

### 1. 需求规格

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| IEEE 830 SRS Format | https://www.geeksforgeeks.org/software-requirement-specification-srs-format/ | Introduction, General Description, Functional Requirements, Interface Requirements, Performance Requirements, Design Constraints, Non-Functional Attributes, Schedule/Budget, Appendices | ✅ 建议采纳 |
| Mountain Goat Software User Stories | https://www.mountaingoatsoftware.com/agile/user-stories | "As a...I want...so that..." 模板, 验收条件 bullet points, 故事拆分原则 | ✅ 建议采纳 |
| Cucumber Gherkin BDD | https://cucumber.io/docs/gherkin/reference/ | Feature, Scenario (Given/When/Then), Background, Scenario Outline+Examples, Step Arguments | ✅ 部分采纳 |
| Atlassian PRD Template | https://www.atlassian.com/agile/product-management/requirements | 项目定义(参与人/状态), 团队目标, 背景与战略契合, 假设, 用户故事, 用户交互, 待决策问题, 明确不做 | ✅ 建议采纳 |
| Google Design Docs Template | https://www.industrialempathy.com/posts/design-docs-at-google | Context/Scope, Goals/Non-Goals, Design, Alternatives Considered, Cross-Cutting Concerns | ✅ 建议采纳 |

### 2. 架构设计

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| arc42 | https://arc42.org/overview | 12 章节：Introduction/Constraints/Context/Strategy/Building Block/Runtime/Deployment/Crosscutting/Decisions/Quality/Risks/Glossary | ✅ 建议采纳 |
| C4 Model | https://c4model.com | 4 层：System Context/Container/Component/Code + 3 补充视图 | ✅ 建议采纳 |
| MADR (Markdown ADR) | https://adr.github.io/madr/ | YAML元数据, Title, Context, Decision Drivers, Options, Decision Outcome, Pros/Cons | ✅ 建议采纳 |

### 3. 详细设计

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| OpenAPI/Swagger v3 | https://swagger.io/docs/specification/v3_0/basic-structure/ | openapi版本, info, servers, paths(endpoints/methods/responses), components(可复用schema) | ✅ 建议采纳 |
| Microsoft Azure API Design | https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design | RESTful设计, URI命名规范, HTTP方法规范, 异步操作, 分页过滤, 版本控制, HATEOAS | ✅ 建议采纳 |
| Zalando RESTful API Guidelines | https://opensource.zalando.com/restful-api-guidelines/ | Principles, REST Basics, REST Design, EVENT Basics, Appendices | ✅ 建议采纳 |
| elsewhencode/project-guidelines | https://raw.githubusercontent.com/elsewhencode/project-guidelines/master/README.md | Resource-Oriented Design, Naming(kebab-case), HTTP Methods, Versioning, Error Responses, Pagination, API Security | ✅ 建议采纳 |

### 4. 测试

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| IEEE 829 Test Plan Template | https://www.softwaretestinghelp.com/test-plan-template/ | Introduction, Scope, Test Strategy, Environmental Needs, Schedule, Exit Criteria, Suspension/Resumption, Risk/Contingencies, Review/Approvals | ✅ 建议采纳 |
| OWASP Web Security Testing Guide v4.2 | https://owasp.org/www-project-web-security-testing-guide/stable | 12 大类 73+ 测试项（信息收集/配置/身份/认证/授权/会话/输入验证/错误处理/弱加密/业务逻辑/客户端/API） | ✅ 建议采纳 |
| Test Case Template | https://www.softwaretestinghelp.com/test-case-template-examples/ | Test Case ID, Priority, Module, Steps, Test Data, Expected Result, Actual Result, Status | ✅ 建议采纳 |
| Regression Testing Checklist | https://www.browserstack.com/guide/regression-testing | 8 步流程：理解变更→选择用例→优先关键→更新→手动/自动→执行→分析→重复 | ✅ 建议采纳 |
| Performance Test Plan (盲区补充) | https://www.guru99.com/performance-testing.html | Load Model, Metrics Definition, SLA Thresholds, Tool Selection, Test Data Preparation | ✅ 建议采纳 |
| UAT Template (盲区补充) | https://www.softwaretestinghelp.com/user-acceptance-testing-uat-template/ | UAT Test Cases, Acceptance Scenarios, Sign-off Sheet, Defect Log | ✅ 建议采纳 |

### 5. 安全

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| OWASP ASVS | https://owasp.org/www-project-application-security-verification-standard | v5.0.0, 需求编号格式 v<version>-<chapter>.<section>.<requirement>, L1/L2/L3 验证级别 | ✅ 建议采纳 |
| OWASP Threat Modeling (STRIDE) | https://owasp.org/www-community/Threat_Modeling_Process | 四步：Scope(DFD)→Determine Threats(STRIDE)→Countermeasures→Assess | ✅ 建议采纳 |
| OWASP Secure Coding Practices | https://owasp.org/www-project-secure-coding-practices-quick-reference-guide | 技术无关的通用安全编码 checklist | ✅ 建议采纳 |
| OWASP Docker Security | https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html | 14 条规则（daemon/用户/capabilities/提权/容器间/安全模块/资源/只读/扫描/rootless/Secrets/供应链） | ✅ 建议采纳 |
| Incident Response Plan (盲区补充) | https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final | NIST SP 800-61: Preparation, Detection/Analysis, Containment/Eradication/Recovery, Post-Incident Activity | ✅ 建议采纳 |

### 6. 部署/运维

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| 12-Factor App | https://12factor.net/ | 12 项：Codebase/Dependencies/Config/Backing Services/Build-Release-Run/Processes/Port Binding/Concurrency/Disposability/Dev-Prod Parity/Logs/Admin | ✅ 建议采纳 |
| Microsoft Well-Architected Operational Excellence | https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/checklist | DevOps文化, 标准化运营, 规范开发, 质量保证, IaC, 供应链, 监控, 事件管理, 测试, 自动化, 安全部署 | ✅ 建议采纳 |
| Microsoft Safe Deployment Practices | https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/safe-deployments | Safety/Consistency, Progressive Exposure(Canary/Blue-Green), Health Models, Rollback/Roll Forward | ✅ 建议采纳 |
| DR Plan (盲区补充) | https://www.ibm.com/topics/disaster-recovery-plan | RPO/RTO定义, 恢复步骤, 演练计划, 业务影响分析, 关键资产清单, 通信计划 | ✅ 建议采纳 |

### 7. 代码评审

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| Google Code Review Standard | https://google.github.io/eng-practices/review/reviewer/standard | 核心标准(代码健康持续提升), 检查清单(设计/功能/UI/安全/过度工程/测试/命名/注释/文档/风格), 紧急例外流程 | ✅ 建议采纳 |
| Google "What to Look For" | https://google.github.io/eng-practices/review/reviewer/looking-for | 11 项：Design, Functionality, Complexity, Tests, Naming, Comments, Style, Consistency, Documentation, Every Line, Context | ✅ 建议采纳 |
| Go Code Review Comments | https://go.dev/wiki/CodeReviewComments | 31 项（gofmt/Comment/Context/Copying/Crypto/Error/Imports/Interfaces/Naming/Receivers...） | ✅ 语言相关采纳 |

### 8. 编码规范

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| PEP 8 | https://peps.python.org/pep-0008/ | Code Layout, String Quotes, Whitespace, Comments, Naming Conventions, Programming Recommendations | ✅ 建议采纳 |
| Google Python Style Guide | https://google.github.io/styleguide/pyguide.html | 21 条语言规则 + 19 条风格规则 | ✅ 建议采纳 |
| Airbnb JavaScript Style Guide | https://javascript.airbnb.tech/ | 30+ 章：Types/References/Objects/Arrays/Functions/Arrow/Classes/Modules/Variables/Comparison/Whitespace/Naming... | ✅ 建议采纳 |

### 9. 项目管理

| 来源 | URL | 模板结构 | 采纳 |
|------|-----|---------|------|
| WBS (Work Breakdown Structure) | https://www.workbreakdownstructure.com/ | 层级分解(100%规则), Work Package, WBS词典(boundaries/milestones/risks/owner/costs), Control Accounts | ✅ 建议采纳 |
| RACI Matrix (盲区补充) | https://www.projectmanager.com/blog/raci-matrix-template | Responsible/Accountable/Consulted/Informed 四角色, 任务-人员交叉表 | ✅ 建议采纳 |
| Milestone Planning Guide | https://asana.com/resources/project-milestones | Milestone定义(零工期检查点), 分类(关键任务/阶段结束/重大事件/目标), 与项目阶段对齐 | ✅ 建议采纳 |

---

## 二、AI Agent 提示词工程参考（8 个来源）

| 来源 | URL | 核心方法 | 对 Loop 的价值 |
|------|-----|---------|---------------|
| Anthropic - Building Effective Agents | https://www.anthropic.com/engineering/building-effective-agents | 编排者-工作者模式, 路由, 评估者-优化器, 工具提示词设计, Agent 透明性 | 将编排者-工作者模式应用于 Loop 多步骤任务；工具提示词设计 |
| MetaGPT 角色定义 | https://github.com/geekan/MetaGPT | PREFIX_TEMPLATE: "You are a {profile}, your goal is {goal}", CONSTRAINT_TEMPLATE, STATE_TEMPLATE | 为 Loop 角色使用 {profile}/{name}/{goal} 结构 |
| CrewAI Agent 定义 | https://docs.crewai.com/concepts/agents | role/goal/backstory 三要素, YAML配置, system/prompt/response模板 | 采用声明式三要素, backstory 丰富角色身份 |
| dair-ai Prompt Engineering Guide | https://github.com/dair-ai/Prompt-Engineering-Guide | Zero-Shot, Few-Shot, CoT, 自一致性, 知识生成, 提示链, ToT, ReAct, Reflexion | 推理角色用 CoT, 工具角色用 ReAct, 规划角色用 ToT |
| Few-Shot + CoT 模板 | https://www.promptingguide.ai/techniques/fewshot | 输入-输出演示示例, "Let's think step by step" 触发器, Auto-CoT | 嵌入正确/错误示例, 重推理角色嵌入分步推理 |
| LangChain 结构化输出 | https://docs.langchain.com/oss/python/langchain/structured-output | Pydantic BaseModel, response_format, 验证失败重试, ProviderStrategy/ToolStrategy | Pydantic 模型定义角色输出 schema |
| Instructor 模式提取 | https://python.useinstructor.com/ | 字段级约束(min_length/gt), @field_validator, llm_validator, 自动重试 | 精确抽取 LLM 输出, 输出质量保证 |
| 提示词设计技巧 | https://www.promptingguide.ai/introduction/tips | 角色定义放在开头, 正向表述, 用分隔符(###)区分角色与上下文, 越具体越好 | 改进 SKILL.md 开头, 正向指令, 清晰分隔 |

---

## 三、确定性验证工具配置参考（6 个来源）

| 来源 | URL | 关键配置 | 对 Loop 质量门禁的价值 |
|------|-----|---------|---------------------|
| pytest | https://docs.pytest.org/en/stable/reference/customize.html | pytest.ini: addopts, testpaths, markers, --cov-fail-under=80 | 强制执行覆盖率阈值, mark 区分(gate/slow)测试 |
| ruff | https://docs.astral.sh/ruff/configuration/ | ruff.toml: line-length=88, target-version=py310, select=[E,F,I,N,W,UP], isort | 统一 lint+格式化, 零违规 gate |
| mypy | https://mypy.readthedocs.io/en/stable/config_file.html | strict=True, disallow_untyped_defs=True, per-module overrides | 渐进式类型检查, 零类型错误 gate |
| pre-commit | https://pre-commit.com/#plugins | .pre-commit-config.yaml: repos(ruff/mypy/pytest/bandit), always_run | 每次 git commit 自动化全部检查 |
| GitHub Actions | https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python | python-ci.yml: 多版本测试矩阵, lint/typecheck/test/security jobs, artifact upload | 每次 PR 自动跑全部门禁 |
| bandit | https://bandit.readthedocs.io/en/latest/config.html | bandit.yaml: exclude_dirs, skips, 零高危 gate | 安全 lint，零高危漏洞 gate |

---

## 四、搜集方法说明

- **并行独立搜索**：Agent A 和 Agent B 在不同会话中独立搜索，互不知道对方存在
- **交叉比对**：Agent C 只读 A 和 B 的输出，不对搜索引擎交互，仅做裁判
- **盲区补搜**：Agent D 针对 C 发现的 5 个盲区进行补充搜索
- **提示词参考**：Agent E 专门搜索 Anthropic、MetaGPT、CrewAI 等框架
- **验证工具**：Agent F 专门搜索 pytest/ruff/mypy/pre-commit/CI 配置

**所有来源均通过实际 URL 抓取获取模板结构，非凭记忆编造。**
