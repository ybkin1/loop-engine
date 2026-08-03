# T-0107 修复执行记录（commands.md）

- 任务：T-0107 设计漏洞修复 — P1 context_packager 截断 + P2 全量 + P3 首批
- 修复依据：`.ai/evidence/T-0106/design/audit-design-gaps.md`（编号 D1/D2/D3/D4/D5）
- 日期：2026-08-03
- 执行角色：developer（子智能体）

## 逐项修复记录（编号 | 文件 | 修复方式 | 测试）

### 组 1：context_packager 专项（9 处，`loop_core/context_packager.py`）

| # | 文件 | 修复方式 | 测试 |
|---|------|----------|------|
| D1-1 (P1) | `loop_core/context_packager.py` | 任务卡 `[:1000]` 固定切片 → `_format_task_card()`：按 `## ` 节解析 + token 预算（`TASK_CARD_TOKEN_BUDGET=1500` × 4 字符/token ≈ 6000 字符）+ **AC/验收节优先保留（永不切）** + 丢弃/截断时追加 `…[task card truncated ...]` 标记 | `TestD11TaskCardBudget`（AC 不切 3 项 + 纯文本卡标记） |
| D1-2 (P2) | 同上 | 角色文件按 `max_content` 截断 → `_slice_with_marker()` 追加 `…[truncated N chars]` | `test_role_file_truncation_marked` |
| D1-3 (P3) | 同上 | extra_files `[:2000]` → 命名常量 `EXTRA_FILE_MAX_CHARS` + 显式标记 | `test_extra_file_truncation_marked` |
| D1-4 (P2) | 同上 | knowledge cases `[:3000]` 中段切断 → `_format_knowledge_cases()`：按 **case 边界**截断（丢弃尾部 case），JSON 保持语法完整 + `…[truncated N cases]` 标记 | `test_knowledge_cases_truncated_to_valid_json`（前缀可 json.loads） |
| D2-1 (P2) | 同上 | 1000/2000/3000/5/3 字面量 → 命名常量（`TASK_CARD_TOKEN_BUDGET`/`EXTRA_FILE_MAX_CHARS`/`KNOWLEDGE_CASES_MAX_CHARS`/`MAX_EXTRA_FILES`/`MAX_KNOWLEDGE_CASES`） | `TestNamedConstants::test_truncation_literals_named` |
| D2-8 (P3) | 同上 | git timeout 5/10/5 散落 → `GIT_TIMEOUT_DIFF_STAT/CODE/NAME/REV_PARSE` 命名常量 | `test_git_timeouts_named` |
| D3-2 (P2) | 同上 | `MAX=15000` 死护栏（total 从不递增）→ `_add()` 内 total 真实累计 + 超限节截断/丢弃 + `…[context truncated: total budget exceeded]` 标记（footer 不丢） | `TestD32TotalBudget`（monkeypatch 预算验证真实执行） |
| D4-1 (P2) | 同上 | git diff 段 `except Exception: pass` → 每命令独立捕获：warning 日志 + `## Git Diff Status\n(diff unavailable: ...)` 占位节（不再静默消失） | `TestD41GitDiffFailure` |
| D4-4 (P3/P2 任务卡口径) | 同上 | (a) knowledge cases 损坏静默丢弃 → warning 日志；(b) diff 无缓存 → 进程内缓存（key=(root, HEAD, kind)，同 HEAD 不重跑 git diff，成功才入缓存、上限 64 条目） | `test_corrupt_knowledge_cases_warned` + `test_diff_cache_reuses_same_head` |

### 组 2：P2 全量（11 项）

| # | 文件 | 修复方式 | 测试 |
|---|------|----------|------|
| D1-2 | `loop_core/context_packager.py` | 见组 1（同源修复） | 见组 1 |
| D1-4 | `loop_core/context_packager.py` | 见组 1（同源修复） | 见组 1 |
| D2-1 | `loop_core/context_packager.py` | 见组 1（同源修复） | 见组 1 |
| D2-2 | `loop_core/intent_router.py:558` | `len(triggered_medium) >= 3` → 类常量 `MEDIUM_RISK_ESCALATION_MIN = 3`（静态方法内经类名引用） | `TestD22EscalationThreshold`（常量值 + 行为不变） |
| D3-1 | `loop_core/audit_ledger.py:84` | append 前按行/字节阈值轮转（`DEFAULT_MAX_LINES=10k`/`DEFAULT_MAX_BYTES=10MB`/`DEFAULT_MAX_ARCHIVES=3`，构造可配置）；`_load` 按归档（旧→新）→主文件读入，**链哈希跨归档延续**，verify 完整 | `TestAuditLedgerRotationAndCorrupt::test_rotation_preserves_chain_integrity`/`test_archives_bounded` |
| D3-2 | `loop_core/context_packager.py` | 见组 1 | 见组 1 |
| D4-1 | `loop_core/context_packager.py` | 见组 1 | 见组 1 |
| D4-2 | `hooks/scripts/loop_enforcement.py:213-222` | `is_loop_mode_enforced` state 读取异常 `return False`（fail-open）→ **fail-closed 强化**：`return True` + `STATE_UNREADABLE` warning（与 runtime 投影路径不可用即 BLOCK 语义一致）；正常路径 FULL/STANDARD 判定不变 | `TestD42FailClosed`（缺失/损坏 state → True；三态模式不变） |
| D4-3 | `tools/tool_constraint_check.py:18,21` | 非法 phase `except ValueError: pass` → `phase_problems`/`phase_problem_count` 告警字段返回（约束在无 phase 上下文下运行的可见性） | `TestD43ConstraintCheckPhaseProblems` |
| D5-1 | `loop_core/context_controller.py:444-538` | `_yaml_load_checked()`：PyYAML 不可用/语法错误 → **显式告警**（不再静默降级）；naive 解析结果做 **schema 校验**（复用 `loop_core/schemas/state.schema.json`/`gate.schema.json`，jsonschema 可用时逐条 validate，问题列表上报）；`_load_gates` **解析失败与"无 gate"分开上报**（文件缺失/无 gates 键 = 正常不告警；解析异常/校验失败显式 warning）；`_load_state` 同步告警 | `TestD51YamlFallback`（5 项：fallback 告警/schema 校验/syntax error/无 gate 不告警/主路径零告警） |
| D5-2 | 新模块 `loop_core/front_matter.py` + `loop_core/context_controller.py` + `hooks/scripts/loop_enforcement.py` | **抽共享契约解析模块**：`parse_task_front_matter()` 支持 allowed_paths / developer_agent_id / reviewer_agent_id / mcp_allowed_tools（内联、列表、markdown 表格 `| mcp_allowed_tools | mcp__a |` 三种形态）；context_controller._load_task_contract 与 loop_enforcement.load_task_contract 统一调用；enforcement 在退化环境（陈旧插件缓存无该模块）回退到本地同逻辑副本 `_parse_task_front_matter_legacy`（逐行一致） | `TestD52SharedFrontMatter`（4 项：表格/列表一致、**双路径一致**、legacy 副本一致、controller 含 mcp 字段） |

### 组 3：P3 首批（6 项）

| # | 文件 | 修复方式 | 测试 |
|---|------|----------|------|
| D3-4 | `loop_core/runtime_controller.py:120,490-491` | `runtime-events.jsonl` 追加无轮转 → `_rotate_journal_if_needed()`（`JOURNAL_MAX_BYTES=5MB`/`JOURNAL_MAX_ARCHIVES=3`，追加前检查，best-effort） | `TestD34JournalRotation` |
| D3-5 | `loop_core/async_jobs.py:504-523` | 落盘侧 `_persist` JSONL 无上限 → `_rotate_persist_if_needed()`（`PERSIST_MAX_BYTES=5MB`/`PERSIST_MAX_ARCHIVES=3`，构造可配置 `persist_max_bytes`/`persist_max_archives`） | `TestD35PersistRotation` |
| D4-5 | `loop_core/audit_ledger.py:58-59` | `_load` 损坏行静默跳过 → 逐行计数 + warning（`corrupt_line_count`/`corrupt_lines` 属性；`AuditIntegrity.corrupt_lines` 字段——verify 可区分"已清理"（0）与"被篡改"（>0）） | `TestAuditLedgerRotationAndCorrupt::test_corrupt_trailing_line_reported`/`test_corrupt_middle_line_breaks_chain` |
| D4-7 | `hooks/scripts/loop_enforcement.py:83-96` | 文件哈希读取 OSError `continue` → 记录被跳过文件（`HASH_SCAN_SKIPPED` warning，进程内按文件去重防刷屏） | `TestD47HashSkipWarned`（告警一次 + 去重） |
| D4-8 | `.zcode/tools/transaction_registry.py:158-162` | 裸 `except:` 吞中断 + 冗余双重计算 → 删除整个 try/except（死代码），统一 `Path(root) / ".ai/transaction_registry.yaml"`（str 与 Path root 均正确，修复 str root 潜在 TypeError） | `TestD48TransactionRegistry`（Path/str root 均可写 + 无裸 except 残留） |
| D5-5 | `loop_core/contract_verifier.py:108-146` | fallback 触发条件**收窄为仅 ImportError**：PyYAML 语法错误 → 告警 + 返回空结构（不再 pattern 降级，fail-closed）；仅 ImportError 走 pattern fallback 且产出去向标注 `_parsed_by: "pattern-fallback"` | `TestD55ContractVerifierFallback`（3 项：语法错误空结构/ImportError fallback 标注/PyYAML 主路径零标注） |

### KNOWN_ISSUES 清零

- `.ai/KNOWN_ISSUES.md`：T-0106 登记的 12 条（P1×1 + P2×11）全部移入 Recently Closed，注明「T-0107 修复，v3.12.44」；Open 区保留主会话新登记的 session-source-disabled 项（T-0112 候选，按要求不并入本任务）

### 顺手事项

- `.ai/tasks/T-0106.md` `## Status` in_progress → completed（消除 validate legacy warn）
