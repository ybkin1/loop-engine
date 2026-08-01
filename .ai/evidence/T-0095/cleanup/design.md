# T-0095 遗留清理包 — 设计文档（cleanup）

- task_id: T-0095
- gate_id: G-T-0095-REQUIREMENTS
- 角色: developer（子代理）
- created_at: 2026-08-02T00:00:00+08:00
- 范围: P3 技术遗留系统性清理（T-0086~T-0094 记录项）+ 记录归档项
- 约束: 只改允许路径（.ai/、loop_core/、hooks/、tools/、scripts/、tests/、docs/、.ai/evidence/T-0095/）；不得放宽任何写入拦截；slo.yaml 默认值与 B2 内置一致；不伪造测试结果

---

## 1. 清理项清单与修复方式

| # | 清理项 | 修复方式（文件） | 行为影响 |
|---|--------|------------------|----------|
| 1 | 死导入 `field`（F401） | `loop_core/capability_registry.py` L30：`from dataclasses import dataclass, field` → `from dataclasses import dataclass` | 无（纯 lint） |
| 2 | `.ai/slo.yaml` 显式化 | 新建 `.ai/slo.yaml`（从 `DEFAULT_SLOS` 程序化生成，14 条 SLI 与内置完全一致 + `budget_total_units: 100.0` + `release_fee_units: 5.0` + `window_start/end: null`）；`loop_core/governance_metrics.py::load_slo_config` 增加 fail-closed 语义校验（budget 单位数值/正数、window 成对且可解析、target op/value、severity、budget_share），非法配置 → `DataSourceUnavailableError`（字段名明确）；`loop_core/slo_gate.py` 经 `load_slo_config` 自动生效 | 默认值不变（null window = 全量数据）；缺文件回退内置默认；非法配置从"部分生效/静默忽略"改为明确报错（fail-closed） |
| 3 | guard-events 轮转/上限 | `loop_core/observability.py` GuardEventRecorder：构造参数 `max_lines=10000` / `max_bytes=10MB` / `max_archives=3`；`_append_line` 前 `_rotate_if_needed()`（超限 → `guard-events.jsonl`→`.1`→`.2`…，保留最近 N 个归档，更旧丢弃）；轮转失败静默（append 继续，observation 永不阻断）；`read_events` 读主文件 + 全部保留归档（时间序，不丢事件） | 默认阈值下无归档 → 行为不变；超限后主文件受限、历史进归档（recorder 视角不丢） |
| 4 | env 链统一 | `loop_core/llm/keys.py`：新建规范表 `KEY_TIERS`（key, base_url, protocol 三元组）：LLM→ANTHROPIC→OPENAI→ZCODE，`DEEPSEEK_API_KEY` 降为殿后 legacy 别名 tier（保持既有 fallback 可用）；`KEY_ENV_VARS` 派生；`resolve_api_key` 走 `KEY_TIERS`；新增 `resolve_api_base_url`（与胜出 tier 成对的 base_url，未设 → ""）；`loop_core/llm/zcode_config.py`：`ENV_TIERS = KEY_TIERS`（同一对象，杜绝两处漂移）；`loop_core/llm/__init__.py` 导出 `resolve_api_base_url` | 优先序按任务要求统一为 LLM→ANTHROPIC→OPENAI→ZCODE；DEEPSEEK 仍可解析（仅当四个规范 tier 均未设时）；key 与 base_url 成对 |
| 5 | 引用修复子串边界 | `loop_core/context_loader.py::repair_truncated_references`：最长优先处理 token；已解析 token（含"已为规范形式无需替换"的情形，修复了首次实现漏记该情形导致的双前缀）记录到 `resolved_tokens`；后续 token 若是更长已解析 token 的子串 → 跳过（防 `.ai/.ai/` 双前缀） | 完整路径+丢前缀同文本不再产生双前缀；其余解析语义不变 |
| 6 | metrics_view 顶层非对象 | `loop_core/dashboard_views.py::metrics_view`：`_load_json` 成功后检查 `isinstance(doc, dict)`，非对象 → `_not_available("metrics report top-level JSON is not an object: ...")` | 顶层数组/标量 → NOT_AVAILABLE（原为 AttributeError 崩溃） |
| 7 | SLO 双重开关检查去重 | `loop_core/slo_gate.py`：开关检查只保留一处 —— `check_slo_gate` 顶部（覆盖 budget 路径与 config 路径，且保持"禁用时先短路、不读数据源"语义）；`_check_with_config` 移除重复检查；`.ai/checkers/slo_gate_checker.py` 的 `--slo` 旁路路径补上单次 `slo_gate_enabled` 检查（禁用 → 与原先一致的 DISABLED 结果） | 每条执行路径恰好一次开关检查；禁用+损坏 slo.yaml 仍 DISABLED（短路在配置读取之前） |
| 8 | 只读豁免口径统一 | `hooks/scripts/hook_common.py`：新增单一判定源 `READ_ONLY_TOOLS` + `is_readonly_exempt(tool_name, command, rel=None)`（只读工具 / `is_readonly_command` 只读 Bash → True；执行形态/写命令 → False）；`path_guard.py` 与 `loop_enforcement.py` 删除各自内联表达式与本地常量，统一调用共享函数。应用口径（不变）：path_guard（写入边界守卫）谓词即完整豁免；loop_enforcement 仅在"只读+外部引用"组合下走 EXTERNAL_READ 早退，项目内只读仍走 dispatch/identity 门 | 只收窄或等价，不放松：写入拦截（项目外写入、执行形态、保护区 deny/ask、DISPATCH/IDENTITY 门）全部保持；两 hook 判定源单一，杜绝漂移 |
| 9 | gate_lesson 无锁 RMW | `loop_core/gate_feedback.py`：模块级 `threading.Lock`（进程内），`record_gate_lesson` 的 load→append→save 整体持锁；校验保持在锁外 | 进程内并发 RMW 不丢记录；跨进程仍由 tmp+rename 原子写兜底（文档说明） |
| 10 | HANDOFF 模板引用 | 修正 `.ai/HANDOFF.md` 中 `.ai/evidence/T-0095/evidence-manifest.v1.yaml` 引用 —— 在 `.ai/evidence/T-0095/` 下创建真实存在的 `evidence-manifest.v1.yaml`（EvidenceManifest/v1 schema，列出当前证据文件，sha256/size/mtime_ns 精确绑定），引用即真实路径 | HANDOFF 不再指向不存在的文件；EVIDENCE_MANIFEST_REQUIRED 阻塞项可被满足（后续新增证据由 governance-controller 更新 manifest） |

## 2. AC 映射

| AC | 验收 | 证据（测试 + 结果） |
|----|------|---------------------|
| AC-01 | 死导入清理：F401 0 命中 | `ruff check loop_core/capability_registry.py` 0 命中（见下方 §4）；`tests/test_capability_registry.py::TestT0095DeadImportCleanup` 2 passed |
| AC-02 | slo.yaml 存在 + schema 校验 + 读取生效 | `.ai/slo.yaml` 存在；`tests/test_governance_metrics.py::TestT0095SloConfigExplicitAndValidated` 10 passed（含"仓库 slo.yaml == B2 内置默认"、9 类非法配置 fail-closed）；`tests/test_slo_gate.py` 既有窗口/覆盖测试全过 |
| AC-03 | guard-events 轮转 + 不丢事件 | `tests/test_observability.py::TestT0095EventRotation` 5 passed（行数阈值轮转、字节阈值轮转、归档上限、阈值下不轮转、轮转失败不阻断） |
| AC-04 | env 链次序一致 | `tests/test_llm_layer.py`（+4：base_url 成对、空态、统一优先序、单源表）+ `tests/test_zcode_config.py`（+2：行为一致、规范顺序）共 6 passed |
| AC-05 | 引用修复边界 + metrics_view 顶层非对象 + SLO 双重检查去重 | `tests/test_context_compression.py`（+2：无双前缀）、`tests/test_dashboard.py`（+3：数组/标量/快照）、`tests/test_slo_gate.py::TestT0095ToggleCheckDedup`（+4：两路径各 1 次开关检查、禁用短路、CLI --slo 禁用） |
| AC-06 | 全量测试无回归 | `C:/Python312/python.exe -m pytest tests/ -q` → 见 §4 全量结果 |
| AC-07 | 无约束被弱化 | 写入拦截 diff 审查：item 8 只读豁免仅收窄判定源（两 hook 均未新增任何放行分支；path_guard 执行形态阻断、项目外写入阻断、deny/ask 保护区语义、loop_enforcement EXTERNAL_READ 组合条件与 DISPATCH/IDENTITY 门全部保持）；item 2/7 的 slo.yaml 默认值与内置一致（null window），禁用短路语义不变；全链测试（test_path_guard/test_enforcement/test_hooks）全过 |

## 3. 记录归档项（OUT OF SCOPE，仅记录，不改代码）

| 归档项 | 说明 | 处置 |
|--------|------|------|
| Bash 反斜杠路径 shlex tokenizer | `hooks/scripts/hook_common.py::_extract_paths_from_bash_command` 等用 shlex（POSIX 模式）切 token，Windows 反斜杠路径会被当转义符损坏（tests/test_path_guard.py 中 `outside_path` 统一用正斜杠规避）。改造风险高（影响全部 hook 的路径提取），记录为已知缺陷 | 归档：不在本任务修改；后续任务评估 |
| 粘性不继承 loop_mode | T-0088 P3-2 设计语义：粘性（sticky）不继承 loop_mode 是有意设计，保留 | 归档：设计语义，保留 |
| dev.py POSIX 分支真机验证 | 无 POSIX 主机，`tools/dev.py`（或等价脚本）的 POSIX 分支无法真机验证 | 归档：记录，待有 POSIX 环境时验证 |
| 未知任务 id 边展示语义 | T-0094 P3-2 设计语义：未知任务 id 在 dashboard/边展示中的行为是有意设计，保留 | 归档：设计语义，保留 |

## 4. 验证记录

- ruff（F401 死导入 AC-01）：
  `C:/Python312/python.exe -m ruff check --select F401 loop_core/capability_registry.py` → `All checks passed!`（0 命中）；
  其余改动文件的 F401 命中均为既有代码（hook_common 的 _hook_bash 兼容再导出、
  loop_enforcement 的 DEFAULT_CONFIG 等旧导入、test_dashboard 的 pytest 导入），
  非本次引入（git diff 确认）。
- 新增测试 43 项全过（见 §2 逐项清单；另 test_llm_layer/test_zcode_config 的
  env 链用例 4+2 项全过）。
- 全量回归：`C:/Python312/python.exe -m pytest tests/ -q` → **3521 passed,
  63 skipped, 12 xfailed**（≥3476 基线，无回归）。
- 冒烟：`python .ai/checkers/slo_gate_checker.py .` → decision PASS / HEALTHY /
  exit 0（真实仓库 slo.yaml 生效且门禁健康）。
- 注：全量测试运行会按仓库既有惯例再生成
  `.ai/evidence/T-0087/contract-planes/conformance-report.json`（仅
  generated_at 变化）并向 `.ai/evidence/observability/guard-events.jsonl`
  追加 guard 事件 —— 该行为在历次 release commit 中一致存在（见
  `git log` 该两文件历史），非本次改动引入；无轮转归档残留（无 *.1 文件）。

## 5. 风险与回滚

- 豁免口径统一：单一判定源 + 全链测试（test_path_guard / test_enforcement / test_hooks）锁定行为；任何放宽写入拦截的 diff 均被测试否决。
- slo.yaml 生效：默认值与内置一致（程序化生成 + 一致性测试锁定）；校验失败 fail-closed；回滚 = 删除 `.ai/slo.yaml` 即回到"缺文件用默认"。
- 轮转：阈值可配；默认 10000 行/10MB 下正常仓库不会触发；回滚 = 移除轮转参数即恢复纯 append。
