# T-0106 批 1 — 全仓库设计漏洞排查（只读审计）

- 任务：T-0106（candidate-only 设计任务，零产品代码变更）
- 范围：`loop_core/` + `tools/` + `scripts/` + `hooks/scripts/` + `agents/*/scripts/` + `.zcode/tools/`（全部 .py，排除 tests/ 与 archive/）
- 日期：2026-08-03
- 状态：只读审计完成，产出本清单；修复排布见 T-0107（正确性）与 T-0109（性能/预算）

## 一、方法

### 扫描命令（Git Bash，repo 根）

```
# D1 截断：固定大小切片
grep -rn "\[: *[0-9]\+.\]" loop_core/ tools/ scripts/ hooks/scripts/ agents/ .zcode/tools/ --include="*.py" | grep -v "/test"
# D2 魔法数值：timeout/retry/limit/max
grep -rn "timeout *=\|retry\|max_retr\|MAX_\|_LIMIT\|limit *=" ... --include="*.py" | grep -v "/test"
grep -rn "if len(.*\(>=\|>\) *[0-9]\|len(.*) *> *[0-9]\{1,4\}" ... | grep -v "MAX_\|_LIMIT\|limit\|max_"
# D3 无界操作：while True / open("a")
grep -rn "while True\|while 1\b\|open(.*['\"]a['\"]" ... --include="*.py"
# D3 无 timeout 的 subprocess
for f in $(find loop_core tools scripts hooks/scripts agents .zcode/tools -name "*.py"); do
  grep -q "subprocess\.\(run\|Popen\|check_output\|call\)" "$f" && ! grep -q "timeout" "$f" && echo "NO-TIMEOUT: $f"; done
# D4 静默吞错
grep -rn "except.*pass\|except:" ... --include="*.py" | grep -v "/test"
```

### 人工抽查文件（深读）

- `loop_core/context_packager.py`（全文，已知项核实 + 专项）
- `loop_core/observability.py`、`loop_core/audit_ledger.py`、`loop_core/execution_ledger.py`（账本/事件文件轮转）
- `loop_core/async_jobs.py`（persist 段）、`loop_core/runtime_controller.py`（journal 段）
- `loop_core/intent_router.py`、`loop_core/veto_escalation.py`（阈值魔法数）
- `loop_core/llm/openai_driver.py`、`llm/anthropic_driver.py`、`llm/retry.py`（while True 退出条件核实）
- `loop_core/guard_health.py`、`tools/loop_guard_health.py`、`tools/loop_metrics.py`、`tools/loop_self_audit.py`
- `hooks/scripts/loop_enforcement.py`（except 块逐处核查）、`hooks/scripts/template_injector.py`、`hooks/scripts/content_guard.py`
- `scripts/release.py`、`scripts/rollback.py`、`scripts/dev.py`、`scripts/role_checkers/*.py`
- `.zcode/tools/transaction_registry.py`、`validation_runner.py`、`evidence_manifest.py`、`governor_lib.py`、`continuity_producer.py`、`validate_state.py`
- `agents/*/scripts/*.py`（5 个）、`tools/tool_constraint_check.py`、`tools/tool_safe_bash.py`、`tools/tool_eval.py`、`loop_core/evals.py`

### 排除项

- 已集中命名的常量：`observability.py` 轮转默认值（DEFAULT_MAX_LINES/BYTES/ARCHIVES）、`context_loader.py`（DEFAULT_MEMORY_LIMIT/CITATION_MAX_CHARS/MAX_SUMMARY_LEVELS）、`evals.py`（MAX_CAPTURE_CHARS/DEFAULT_EXEC_TIMEOUT，且有 truncated 标志）、`template_injector.py` MAX_TEMPLATE_CHARS=8000（截断有显式 `### TEMPLATE TRUNCATED` 标记）、`release.py` VALIDATE_STATE_TIMEOUT、`.zcode/tools` 的 RetryPolicy/文件大小上限（1 MiB/2 MiB/closed-list 256）
- `.zcode/tools/` 与 `loop_core/llm/` 的 `while True` 均为有界块读/有界重试（max_attempts/empty_response_retries/deadline），**不是**无界操作
- 测试文件中的意图性魔法值不列入

---

## 二、发现清单（维度 × 域）

### D1 启发式截断（8 项）

| # | 位置 | 严重度 | 影响 | 修复方向 |
|---|------|--------|------|----------|
| D1-1 | `loop_core/context_packager.py:42` | **P1** | 任务卡 `read_text()[:1000]` 字符截断、无任何标记；实测 T-0105.md 全长 4363 字符，截断点落在业务范围中段，AC/验收节在 1000 字符之后被整体切掉——子代理拿到的是"无 AC 的任务卡" | 按 token 预算截断 + 优先保留 AC/验收节 + 追加 truncated 标记（T-0106 已知项，确认） |
| D1-2 | `loop_core/context_packager.py:62` | P2 | 角色指定文件按 `[:spec["max_content"]]`（2000–8000）截断且无标记，文件超限时子代理无感知内容被砍 | 截断处加 `…[truncated N chars]` 标记 |
| D1-3 | `loop_core/context_packager.py:68` | P3 | extra_files 按 `[:2000]` 截断无标记 | 同上，统一标记 |
| D1-4 | `loop_core/context_packager.py:76` | P2 | knowledge cases `json.dumps(...)[:3000]` 可能切断 JSON 中段，产出语法无效的 JSON 片段且无标记，子代理可能尝试解析而误判 | 截断到完整对象边界或加标记 |
| D1-5 | `loop_core/security_scanner.py:190,198,206,219`、`loop_core/design_reviewer.py:95,104` | P3 | 违规 snippet `[:100]` 截断无省略号标记（显示用，影响低） | 统一 `…` 标记 |
| D1-6 | `loop_core/executor.py:813` | P3 | 失败 stderr `[:500]` 截断无标记，可能切断根因尾部 | 加标记；或保留尾部 + 长度提示 |
| D1-7 | `agents/security-engineer/scripts/run_security_scan.py:137,142,143` | P3 | npm/pip audit 输出 `raw[:500]` 截断后原样返回调用方，无 truncated 标志，下游可能把部分输出当完整结果 | 返回截断标志/长度字段 |
| D1-8 | `tools/loop_self_audit.py:81,138-139` | P3 | 审计输出尾部截断 4000/2000/800/400 字面量（见 D2-7），截断隐含无标记 | 命名常量 + 标记 |

### D2 魔法数值/字符串（8 项）

| # | 位置 | 严重度 | 影响 | 修复方向 |
|---|------|--------|------|----------|
| D2-1 | `loop_core/context_packager.py:42,68,76,65,74` | P2 | 1000/2000/3000/5(extra_files)/3(cases) 散落字面量未命名；ROLE_CONTEXT 每角色 max_content 重复表（2000–8000）也是硬编码分布 | 集中为常量或 config.yaml 节 |
| D2-2 | `loop_core/intent_router.py:558` | P2 | `len(triggered_medium) >= 3`：中风险因素 ≥3 → 升级 loop 模式，升级决策阈值魔法数，调参无集中位置 | 命名常量（如 `MEDIUM_RISK_ESCALATION_MIN=3`） |
| D2-3 | `loop_core/intent_router.py:612` | P3 | `len(domains) >= 4 and sum(risk_factors.values()) <= 2` 置信度惩罚阈值魔法数 | 同上，集中配置 |
| D2-4 | `loop_core/intent_router.py:637,790` | P3 | `len(kw) > 3` 关键词长度阈值重复两处 | 命名常量复用 |
| D2-5 | `loop_core/veto_escalation.py:245` | P3 | `len(distinct_roles) >= 3` 升级 USER_GATE 规则阈值魔法数（有注释说明但未命名未集中） | 命名常量 |
| D2-6 | `hooks/scripts/content_guard.py:71,76`、`hooks/scripts/loop_enforcement.py:630`、`scripts/rollback.py:207`、`tools/tool_evidence_chain.py:21,41`、`tools/tool_cost_tracker.py:20`、`scripts/upgrade.py:251` | P3 | `timeout=30` 至少 6 文件重复散落；`loop_core/guard_health.py:247,258` 另有两处 timeout=20；同值无集中常量，调优易漏 | 集中为 hook 工具共享常量/配置 |
| D2-7 | `tools/loop_self_audit.py:81,138-139` | P3 | 尾部截断 4000/2000/800/400 未命名（与 D1-8 同源） | 命名常量（如 REPORT_STDOUT_TAIL） |
| D2-8 | `loop_core/context_packager.py:46,49,54` | P3 | git 命令 timeout=5/10/5 字面量（每处不同值且无注释理由） | 命名常量或按命令类型统一 |

### D3 无界操作（8 项）

| # | 位置 | 严重度 | 影响 | 修复方向 |
|---|------|--------|------|----------|
| D3-1 | `loop_core/audit_ledger.py:84` | P2 | 核心审计账本 append 无轮转/归档/保留策略（observability 有 10k 行/10MB/3 档轮转，execution_ledger 有 200 条 checkpoint，唯独 audit_ledger 没有）；`self._entries` 全量驻内存，长生命周期仓库无界增长 | 对齐 observability 轮转策略或按条目数归档 |
| D3-2 | `loop_core/context_packager.py:37-38,61,67,71,94` | P2 | `MAX=15000` 全局护栏是死代码：`total` 从不递增，`total < MAX` 恒真，上下文实际无全局上限（新增文件清单/节时静默超限） | 修 total 递增逻辑或删除死护栏换真实预算 |
| D3-3 | `loop_core/execution_ledger.py:184-192` | P3 | checkpoint 归档文件（`.YYYYMMDDTHHMMSS.jsonl`）无保留策略无限累积；且归档即重置链（root_hash），跨归档边界的篡改主链检测不到 | 保留 N 份归档 + 跨归档链延续/校验归档链 |
| D3-4 | `loop_core/runtime_controller.py:120,490-491` | P3 | `runtime-events.jsonl` 追加无轮转，事件每状态变更写一行，长期无界 | 复用 observability 轮转或定期归档 |
| D3-5 | `loop_core/async_jobs.py:504-523` | P3 | 可选持久化 `_persist` JSONL 追加无轮转（内存侧有 DEFAULT_MAX_HISTORY=500，落盘侧无上限） | 落盘侧加轮转/上限 |
| D3-6 | `scripts/role_checkers/scope_drift_detector.py:15`、`review_coverage_checker.py:8` | P3 | `git diff` subprocess 无 timeout（全仓库仅这两处 + loop_self_audit 的 git_commit 无 timeout） | 补 timeout=10 + 异常处理 |
| D3-7 | `scripts/dev.py:391` | P3 | dev 输出日志 `open("a")` 无轮转（dev 工具，影响低） | 截断/轮转或忽略（文档化） |
| D3-8 | `tools/loop_self_audit.py:88-92` | P3 | `git rev-parse --short HEAD` 无 timeout 无异常处理：git 缺失/挂起时整个自审计 crash（对比 `evals.py:664` 同命令有 timeout=10 + 兜底） | 补 timeout + try/except 返回空串 |

### D4 静默吞错（11 项）

| # | 位置 | 严重度 | 影响 | 修复方向 |
|---|------|--------|------|----------|
| D4-1 | `loop_core/context_packager.py:57-58` | P2 | git diff 整段 `except Exception: pass`：Changed Files / Code Diff 节静默消失，子代理无感知（无日志无标记） | 捕获后记 warning + 上下文节加"diff unavailable"占位 |
| D4-2 | `hooks/scripts/loop_enforcement.py:214-219` | P2 | `is_loop_mode_enforced`：state 读取异常 → return False（fail-open），loop 强制静默关闭、后续 hook 全部按非 loop 模式放行；与同文件 runtime 投影路径（:1771-1777）fail-closed 语义不一致 | 异常时 fail-closed（BLOCK）或显式告警并降级 |
| D4-3 | `tools/tool_constraint_check.py:18,21` | P2 | 非法 phase 值 `except ValueError: pass` 静默丢弃，约束在无 phase 上下文下运行，可能产生误导性 PASS/BLOCK | 返回错误或告警字段 |
| D4-4 | `loop_core/context_packager.py:77-78` | P3 | knowledge cases 损坏静默丢弃（与 D4-1 同文件同类模式） | 记 warning |
| D4-5 | `loop_core/audit_ledger.py:58-59` | P3 | `_load` 遇损坏行静默跳过，verify 无法区分"已清理"与"被篡改" | 记录损坏行号/计数 |
| D4-6 | `loop_core/observability.py:209-210` | P3 | 读事件文件损坏行静默跳过（无日志无计数），与 record() 侧 failures 计数不对称 | 记 logger.warning/计数 |
| D4-7 | `hooks/scripts/loop_enforcement.py:94` | P3 | 文件哈希读取 OSError continue，防篡改扫描集静默不完整 | 记录被跳过文件 |
| D4-8 | `.zcode/tools/transaction_registry.py:161` | P3 | 裸 `except:`（会吞 KeyboardInterrupt/SystemExit）+ 无日志；且 try 块内为冗余双重计算（root 为 str 时 Path 除法会抛 TypeError，属双类型防御而非纯死代码） | 删除冗余 try/except 或收窄并加日志 |
| D4-9 | `scripts/role_checkers/scope_drift_detector.py:8`、`review_coverage_checker.py:13` | P3 | 裸 `except:`（yaml 导入降级 / 返回 INVALID），无日志；`yaml=None` 后返回的 error 信息有限 | 收窄异常 + 记原因 |
| D4-10 | `agents/system-architect/scripts/analyze_dependencies.py:71` | P3 | `except (FileNotFoundError, TimeoutExpired, JSONDecodeError, Exception): return None`（宽捕获 + 冗余 Exception）：madge 失败静默返回 None，下游可能报告"无依赖" | 区分失败原因并上报 |
| D4-11 | `agents/module-architect/scripts/validate_contract.py:279,342` | P3 | `except (SyntaxError, Exception)` 冗余宽捕获，解析失败静默返回空导出 | 收窄 + 记录失败文件 |

### D5 启发式推断（7 项，批 2 补充扫描 2026-08-03）

> 扫描方法：`re.`/`startswith`/`split`/位置推断模式全量 grep + 对每个命中点核实
> "是否以正则/位置/顺序推断替代显式契约（schema/结构化字段）"。

| # | 位置 | 严重度 | 影响 | 修复方向 |
|---|------|--------|------|----------|
| D5-1 | `loop_core/context_controller.py:444-538`（`_naive_yaml_parse`，被 `_yaml_load` :429-442 在 PyYAML ImportError 时静默降级调用；`_load_state`/`_load_gates` :362,376 消费） | **P2** | 缩进/位置推断的 YAML 子集解析替代 schema 校验：`list_keys=["gates","tasks"]` 硬编码（:473），其他列表键静默丢弃；全部值降为字符串（类型保真丢失，如 `loop_mode`/`status` 布尔与数值语义不可辨）；畸形 YAML 静默产出部分 dict——gate 列表解析不全时授权决策基于不完整数据，且无任何告警（对比 `governance_metrics.load_guard_events` :303-322 的 strict-parse fail-closed 风格） | 保留 PyYAML 主路径，但 fallback 改为显式告警 + 解析结果 schema 校验（`loop_core/schemas/` 已有 gate/state schema 可复用）；`_load_gates` 解析失败与"无 gate"分开上报 |
| D5-2 | `hooks/scripts/loop_enforcement.py:259-295` vs `loop_core/context_controller.py:400-414` | **P2** | 同一任务卡 front-matter（allowed_paths / developer_agent_id / reviewer_agent_id / mcp_allowed_tools）存在**两套独立的前缀推断解析器**，行为分歧：enforcement 版支持 `mcp_allowed_tools` 的 `\|` markdown 表格格式（:266-276），context_controller 版不支持；同一契约两种解释，路径放行决策取决于运行的是哪个解析器；契约格式演进需同步两处（风险：只改一处） | 抽共享契约解析模块（T-0107 落地），enforcement 与 context_controller 统一调用；front-matter 格式契约化（schema + 解析测试） |
| D5-3 | `loop_core/context_loader.py:186-209`（正则 key 字段推断）、`:1283`（`### Step \d+:` 标题位置推断框架步骤）、`:1299-1324`（`_select_relevant_sections` 角色名→节名关键词匹配，docstring 自认 "simple heuristic"） | P3 | 任务卡/文档的结构化字段（task_id/gate_id/phase/decision）靠自由文本正则推断而非读取结构化字段；框架步骤靠标题编号位置推断；文档节选择靠角色名关键词猜测——文档格式措辞微变即静默改变加载内容，无校验 | key 字段改读任务卡 front-matter 结构化区（衔接 D5-2 的契约解析）；节选择改读 `.ai/README` Switchboard 路由表（BH 融合 F4） |
| D5-4 | `loop_core/intent_router.py:626-646`（`_detect_domains` 关键词子串匹配）、`:649-738`（`_extract_risk_factors` 风险因子关键词推断）、`:1171-1177`（`_INTENT_SPLIT_RE` 按中文标点/连接词正则切分自由文本为多意图） | P3 | 意图/风险推断依赖词表与正则启发式而非显式元数据：词表膨胀误匹配（如 "role" 命中 auth 因子）、分割正则依赖中文标点 lookbehind，输入风格变化即误分割（意图数/风险因子数影响 loop_mode 升级决策，见 D2-2 阈值）。优点：词表已集中（`DOMAIN_KEYWORDS` 常量） | 词表/正则外提为 `intent_keywords.py` 常量表（批 3 拆分项）；路由决策保留启发式但输出不确定性可观测（分析结果入 IntentBrief 日志） |
| D5-5 | `loop_core/contract_verifier.py:108-146`（`_parse_yaml_content` fallback） | P3 | contract 文件 PyYAML 解析失败/不可用时按 `- function:` 与 `- test_\w+` 子弹项**位置推断**重建结构：非 function/tests_required 字段静默丢弃（:126-141 fallback 无日志，仅 :116 有一次 warning）；顺序敏感（仅 function 行之后的 test 行被收集） | 收窄 fallback 触发条件（仅 ImportError 而非任意 Exception）；fallback 产出去向标注不完整；字段完整性与 schema 校验测试 |
| D5-6 | `loop_core/memory_service.py:52-70`（验收报告解析正则族：`_GATE_LINE_RE`/`_VERDICT_RE`/`_LEGACY_HEADING_RE`/`_DATE_RE`） | P3 | 验收报告的结构化字段（Gate/裁决/日期/遗留节）靠 markdown 格式正则推断：报告模板措辞/顺序变化（如 Gate 行改加粗）即静默丢失知识抽取；裁决回退正则 `_VERDICT_RE`（:63）与真实裁决格式脱节时无感知 | 报告生成端输出结构化 front-matter（衔接 F7 finding 契约化）；解析侧对未命中行计数上报（`MemoryExtractionReport` 已可扩展） |
| D5-7 | `scripts/role_checkers/implementation_design_diff.py:13-14` | P3 | 用反引号代码引用正则从架构文档推断"设计了哪些文件"，再与文件树前缀匹配判 DRIFT：文档中任意示例性/说明性代码引用（非设计声明）被当作设计声明，产生误报；目录引用 `\`x/\`` 与真实文件前缀匹配规则亦为启发式 | 设计文件清单改读设计文档显式声明区（如 front-matter `designed_files:`）；正则推断仅作提示不作 DRIFT 判定依据 |

D5 域分布：`loop_core/` 5 项（D5-1/3/4/5/6）、`hooks/scripts/` 1 项（D5-2，与 loop_core 双解析器同源）、`scripts/` 1 项（D5-7）。

---

## 三、汇总统计

### 按维度

| 维度 | 数量 | P1 | P2 | P3 |
|------|------|----|----|----|
| D1 启发式截断 | 8 | 1 | 2 | 5 |
| D2 魔法数值 | 8 | 0 | 2 | 6 |
| D3 无界操作 | 8 | 0 | 2 | 6 |
| D4 静默吞错 | 11 | 0 | 3 | 8 |
| D5 启发式推断 | 7 | 0 | 2 | 5 |
| **合计** | **42** | **1** | **11** | **30** |

### 按代码域

| 域 | 数量 | 主要问题 |
|----|------|----------|
| `loop_core/` | 26 | context_packager 截断/超时/死护栏/吞错群（D1-1~6、D2-1、D2-8、D3-2、D4-1/4）、audit_ledger 无轮转+损坏行（D3-1/D4-5）、execution_ledger 归档无保留（D3-3）、runtime_controller/async_jobs 轮转（D3-4/5）、observability 读侧计数（D4-6）、intent_router/veto 阈值（D2-2~5）、D5 启发式族（D5-1/3/4/5/6） |
| `tools/` | 4 | loop_self_audit 尾部字面量（D2-7/D1-8/D3-8）、tool_constraint_check 吞 phase（D4-3） |
| `scripts/` | 4 | role_checkers 无 timeout + 裸 except（D3-6/D4-9）、dev.py 日志无轮转（D3-7）、反引号正则推断（D5-7） |
| `hooks/scripts/` | 4 | timeout=30/20 散落（D2-6，主域）、loop_enforcement fail-open（D4-2）、哈希跳过（D4-7）、双解析器（D5-2） |
| `agents/` | 3 | 宽捕获静默降级（D4-10/11）、audit 输出截断无标志（D1-7） |
| `.zcode/tools/` | 1 | transaction_registry 裸 except（D4-8，治理工具整体边界良好） |
| **合计** | **42** | 按主文件域逐项计（复算：D1:8、D2:8、D3:8、D4:11、D5:7）；跨域条目 D2-6（涉 hooks/scripts+scripts+tools）计入主域 hooks/scripts |

### P1 清单

- **P1-1**（D1-1）：`loop_core/context_packager.py:42` — 任务卡按 1000 字符静默截断且无标记，AC/验收节被切掉，子代理在无 AC 下执行角色职责（用户关切核心案例，确认）。

---

## 四、与 T-0106 任务卡已知项核对

任务卡 context_packager 专项预期 ≥5 处缺陷，逐项核对：

| 已知项（任务卡描述） | 核对结论 |
|---------------------|----------|
| 1000 字符截断 | **确认**：`context_packager.py:42`，任务卡 `[:1000]` |
| 截断在 AC 前（AC 节被切） | **确认**：T-0105.md 实测 4363 字符，截断点（1000）落在业务范围中段，AC/验收节被切 |
| 字符 vs token | **确认**：全部上限（1000/2000/3000/max_content 2000–8000/MAX=15000）均为字符，无 token 预算 |
| diff 无缓存 | **确认**：`context_packager.py:46-54` 每次 build_context 重跑 `git diff HEAD~1`，无缓存 |
| git 命令无 timeout 保护 | **未复现（任务卡描述过时）**：`:46/49/54` 均有 timeout=5/10/5；但 timeout 值为散落字面量（D2-8） |
| 新增（任务卡未列） | **D3-2** `total` 从不递增 → MAX=15000 死护栏；**D4-1** git diff 段静默吞错；**D3-1** audit_ledger 无轮转；**D4-2** loop_enforcement fail-open；**D2-2/2-5** intent_router/veto 升级阈值魔法数；**D4-3** tool_constraint_check 吞 phase 等 |

专项小结：任务卡 5 项中 4 项确认、1 项（git 无 timeout）未复现；另新增 ≥6 项同源问题。context_packager 单独聚合缺陷：D1-1~4、D2-1、D2-8、D3-2、D4-1、D4-4，共 9 处。

---

## 五、建议排布（供批 4 整合参考）

- **T-0107（正确性修复）**：P1-1 + 全部 P2（D1-2/4、D2-1/2、D3-1/2、D4-1/2/3）+ D5-1/2（解析器收敛，P2）
- **P3 归属（T-0106 P2-1 排布补齐，与 plan-task-roadmap.md『P3 项归属总表』一致）**：全部 30 项 P3 按内容分派——T-0107（D3-4/5、D4-5/7/8、D5-5）、T-0108（D1-3/7、D2-8、D4-4/10/11、D5-3/6/7）、T-0110（D1-5/6/8、D2-3~7、D3-6/8、D4-9、D5-4）、T-0111（D3-3、D4-6）；T-0109（BH 分层期）不承接 P3
- **不实施（记录留档）**：dev.py 日志无轮转（D3-7，dev 内部工具影响低，audit 原判"文档化即可"）；D1-5 原判"文档化即可"，经 P2-1 归入 T-0110 M-10 截断字面量集中一并落地（统一标记）
- **随 BH 融合消化**：D5-3 节选择改读 Switchboard（F4）、D5-7 设计文件清单改读架构文档 front-matter 声明区（F4）、D5-6 报告 front-matter 契约化（F7）、D1-7/D4-10/11 随 F7 agents 脚本输出收敛（截断标志/失败原因上报）
