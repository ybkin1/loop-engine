# T-0100 独立审查报告（independent-reviewer）

- 任务：T-0100 质量验收 findings 修复包（F-03~F-06，5 项修复）
- 审查者：independent-reviewer（独立验证，不复述 developer 报告）
- 审查时间：2026-08-02（UTC+8）
- 环境：Windows 10 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
- 基线：git HEAD `387c7be`（v3.12.38 T-0099）；工作树含全部 T-0100 改动（未提交）

---

## 裁决：GO（第二轮复验更新，2026-08-02）

> 第一轮裁决 CONDITIONAL_GO（见下文原文）；P2-1/P2-2 条件修复后经第二轮
> 独立复验全部满足（正则一致、纯追加零弱化、测试 27+100 全绿、独立 probe
> 10/10 PASS），裁决更新为 **GO**。复验证据见"P2 修复复验（第二轮）"节。

### 第一轮裁决原文（CONDITIONAL_GO，2026-08-02）

修复真实性、AC-01~AC-06 全部 PASS、约束零弱化总体保持（slo_gate 门禁判定层原样、
SKIP 附原因不掩盖真实阻断）。但 F-06 的两条"规则精度修正"引入两处**检测覆盖回退**
（见 P2-1/P2-2），需按下列条件处理后放行：

- **P2-1（必须处理）**：`run_security_scan.py` 不再检出 **split-literal SQL 拼接**
  （如 `"SELECT " + cols + " FROM " + tbl + " WHERE id=" + uid`）。旧规则
  （`["'].*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b.*["']\s*\+`）可检出（HIGH 阻断级），
  新语句上下文规则 `_SQL_STMT` 漏检（已实测）。处理方式二选一：
  1. 恢复检测：在 `+`/`%` 系规则中追加"字面量起始即 SQL 关键词 + 拼接/格式化运算符"
     分支（建议正则见下文，已实测零误报于 UI 标签）；或
  2. 显式文档化该限制并补测试钉住（接受为已知局限）。
- **P2-2（必须处理）**：`obj["innerHTML"] = userInput` 类 **bracket-access HTML sink**
  不再检出。旧规则（无 lookaround）可检出（MEDIUM），新规则 `(?<!["'])…(?!["'])`
  将其排除（已实测）。处理方式同上（建议正则见下文，已实测 `"innerHTML XSS"` 描述
  文本与只读索引访问均不误报）。

P3 观察项（不阻断，见"观察项"节）：`bump --dry-run` 子命令后置形式不支持；
pip-audit CVSS 向量 severity 不计入 HIGH（预存限制）；wave-2 常量接线后需移除；
`.zcode-plugin/plugin.json` 应纳入后续任务 allowed_paths。

---

## P2 修复复验（第二轮，2026-08-02）— 裁决更新为 GO

P2-1 / P2-2 按 3.3 节建议正则修复，本轮独立复验（不复述 developer 报告，
全部重新执行）结论：**通过，零弱化，零回归**。裁决由 CONDITIONAL_GO 更新
为 **GO**。复验证据：

### 1. diff 审查（`git diff agents/security-engineer/scripts/run_security_scan.py`）

- 工作树未提交，diff 相对 HEAD `387c7be`；P2 增量由代码注释
  `P2-1/P2-2 (T-0100 独立审查)` 标记定位：
  - **P2-1**：HIGH_RISK_PATTERNS 追加新条目
    `("SQL concatenation (split literal)", re.compile(r"""["']\s*(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+(?:TABLE|DATABASE|INDEX|SCHEMA|VIEW))\s+[^"']*["']\s*[+%]""", re.IGNORECASE))`
    —— 与 3.3 节建议正则**逐字符一致**（实现用三引号 raw string，内容相同）。
  - **P2-2**：`unsafe HTML binding` 规则扩展为
    `(?:(?<!["'])(?:innerHTML|outerHTML|insertAdjacentHTML)(?!["'])|\.(?:innerHTML|outerHTML|insertAdjacentHTML)\s*=|\[["'](?:innerHTML|outerHTML|insertAdjacentHTML)["']\]\s*=)`
    —— 原 lookaround 分支**原样保留**为第一 alternative，追加的两分支与
    3.3 节建议（`\.(...)\s*=` 与 `\[["'](...)["']\]\s*=`）verbatim 一致。
- **追加而非替换**：f-string / `+` / `%` / raw SQL execute 四条 `_SQL_STMT`
  规则原样在（第一轮 F-06 状态，未回退）；原 lookaround HTML 分支原样在。
- **无其他行为改动**：P2 增量仅上述两处规则 + 注释 + 测试；规则清单其余
  条目与第一轮审查状态一致（逐条对照 diff 确认）。

### 2. 弱化检查（diff 删除行逐条核对）

- P2 增量**零删除行**（纯追加）。
- 相对 HEAD 的删除行全部属于第一轮已审查的修复本体：F-04 合成 HIGH 删除、
  npm/pip audit 三元组返回重构、F-06 的 SQL/HTML 精度收紧与白名单新增、
  旧 `+` 规则 `\b(...)\b` 关键词版 → `_SQL_STMT` 版。这些是第一轮
  CONDITIONAL_GO 时已接受的改动，非本轮增量；其中 F-06 造成的两处回退
  正是 P2-1/P2-2 补回的对象。**无既有规则被放松**（probe 亦验证
  `"SELECT * FROM users WHERE name=" + name` 单字面量完整形态仍由 `+` 规则
  命中）。

### 3. 测试验证

- `pytest tests/test_security_scan_whitelist.py tests/test_security_dependency_scan.py -q`
  → **27 passed**（0.78s），与预期一致。
- `pytest tests/ -q -k "security"` → **100 passed, 23 skipped**（环境性跳过，
  与 developer 记录一致；无回归）。
- 新增 5 例用例内容抽查（tests/test_security_scan_whitelist.py：
  TestSplitLiteralSqlDetection 3 例 + TestBracketAccessHtmlSink 2 例）：
  split-literal SELECT/UPDATE/DELETE/DROP/INSERT/`%` → HIGH 且 blocked 保持；
  bracket 三关键词赋值 → MEDIUM；`"SELECT color"` 类 UI 标签不误报；
  `x = obj["innerHTML"]` 只读索引访问不误报。描述字符串不误报由既有
  test_html_keyword_in_string_literal_not_reported 覆盖（PASS）。

### 4. 独立 probe（/tmp/t0100_p2_probe.py，走 run_injection_scan 全流程）

10 组样例 **10/10 PASS**：

| 样例 | 预期 | 实测 |
|------|------|------|
| `"SELECT " + cols + " FROM " + tbl + " WHERE id=" + uid` | HIGH split literal | HIGH ✓ |
| UPDATE/DELETE/DROP/INSERT 跨字面量变体 | HIGH | HIGH ✓ |
| `"SELECT %s FROM users" % (uid,)` | HIGH | HIGH ✓ |
| `f"SELECT * FROM users WHERE name={kw}"` | HIGH f-string（原规则） | HIGH ✓ |
| `"SELECT * FROM users WHERE name=" + name` | HIGH `+`（原规则未放松） | HIGH ✓ |
| `obj["innerHTML"]=x` / `el['outerHTML']=x` / `target["insertAdjacentHTML"]=x` | MEDIUM | MEDIUM ✓ |
| `el.innerHTML = userInput` 直接赋值 | MEDIUM（原语义） | MEDIUM ✓ |
| `x = obj["innerHTML"]` 只读索引 | 不报 | 不报 ✓ |
| `"SELECT color"` / `"UPDATE profile"` / `"DELETE entry"` / `"DROP menu"` UI 标签 | 不报 | 不报 ✓ |
| `"description": "innerHTML XSS"` 描述文本 | 不报 | 不报 ✓ |

端到端 overall blocked（high=13, medium=5）——真实注入形态阻断语义保持。

### 5. 复验结论

P2-1/P2-2 修复与审查报告 3.3 节建议正则 verbatim 一致、纯追加零弱化、
无行为外溢；测试与独立 probe 双重确认 split-literal SQL（HIGH 阻断级）与
bracket-access HTML sink（MEDIUM）恢复检出，且 UI 标签 / 只读索引 /
描述字符串零误报。**第二轮裁决：GO**（原 P2 条件全部解除）。

---

## 一、逐项 AC 验证结果

### AC-01（F-03 bump 机制 + 版本对齐）— PASS

实测命令与结果：
- `C:/Python312/python.exe scripts/release.py bump --help` → 子命令存在（`--to`/`--title`）。
- `bump --to 3.12.39` → 幂等 no-op（exit 0，"已是 3.12.39"）；`bump --to 3.12` → 非法版本
  exit 2；`--dry-run bump --to 9.9.9` → 只打印计划（8 载体清单），exit 0。
- 版本载体实测 10 字段全部 = 3.12.39：pyproject / loop_core::__version__ /
  src_loop_engine::__version__ / plugin.json / CHANGELOG 首条目 / README / docs 头部+表格 /
  version-manifest 投影 2 字段。
- 原子写实现核对：`_atomic_write` = 同目录 `tempfile.mkstemp` + `os.replace`，异常时清理
  临时文件并重抛（tests/test_release_bump.py 覆盖无残留与失败保原样）。
- `step_version_sync` diff 仅失败文案变化（补充"先 bump 再提交"约定），判定逻辑
  `version != git_ver → False` 原样；实测 `release.py check` 当前如实阻断
  （pyproject=3.12.39 vs git HEAD=3.12.38，exit 1）—— fail-closed 未被弱化，
  提交 v3.12.39 后自愈。
- `check --dry-run` 与 `--dry-run check` 两种写法均实测可用。

### AC-02（F-01 registry --json 崩溃）— PASS

- 实测 `tools/tool_registry_status.py --json` → exit 0，stdout 为合法 JSON
  （`json.loads` 通过），`integrity.overall=PASS`，stderr 为空（无 UnboundLocalError）。
- 实测文本模式 → exit 0，"Overall: PASS"。
- 修复核对：`death = integrity["death"]` 提前到分支前统一绑定（仅移动一行）；退出码
  语义（0 健康 / 1 missing/drift / 2 guard fail-closed）未动（读源码确认）。
- 测试 3 例全绿，含 guard 不健康时 `--json` 仍 exit 2（fail-closed 回归测试）。

### AC-03（F-04 pip-audit SKIPPED）— PASS

- 实测全仓库扫描：dependency_scan = skipped，counts 全零，reason 明确
  （"pip-audit 环境不可用（exit=1）" + stderr 尾行 traceback）；overall PASS，exit 0。
- 与旧版 diff 核对：合成 HIGH（旧 `counts["HIGH"] = max(1, ...)`）已删除；真实 CVE
  （exit=1 + 可解析漏洞 JSON）仍走原计数逻辑 → HIGH/CRITICAL → blocked
  （tests/test_security_dependency_scan.py::test_real_cve_findings_still_block /
  test_real_blocked_still_blocks_overall 覆盖）。
- SKIP 触发面 = 命令缺失 / 超时 / 执行异常 / 非零退出且输出不可解析 / 项目类型未知，
  均附原因（工具名 + exit 码 + stderr 尾行）；零退出无输出视为无漏洞（与原行为一致）。
- 判断点：非零退出 + 输出不可解析归为"环境不可用"而非"漏洞证据"——对 pip-audit 固定
  JSON 输出形态合理，且 SKIP 透明呈现（不进 blocked_by，但也不声明干净），不掩盖阻断。

### AC-04（F-05 口径统一 + advisory）— PASS

- 实测（脚本直接调用）：`build_report('.', releases=r).budget` 与
  `check_slo_gate('.', releases=r).budget` 在 releases=0/1/3 下 7 字段逐字段一致
  （consumed 0.0/5.0/15.0，remaining 100.0/95.0/85.0，status HEALTHY/CONSUMING）——
  口径差异（T-0099 的 metrics 0.0 vs slo_gate 5.0）根因为调用点默认值不同，现已收敛。
- `release_fee_consumption` 为单一实现，`compute_error_budget` 调用它；
  slo_gate 经 `compute_error_budget` 引用同一函数（读源码确认，slo_gate.py 无平行实现）。
- 实测 `tools/loop_metrics.py --report`：status PASS（修复前 NOT_VERIFIED）、
  missing 0、advisories 14 项逐条列出（3 个 wave-2 源 + 5 个 DORA + 6 个 SLI），
  notes 含"部分源未接线"汇总。
- fail-closed 保持验证：已接线源（gates/task_graph/guard-events）缺失或不可解析 →
  仍 NOT_VERIFIED（tests: test_wired_source_missing_still_not_verified /
  test_unparseable_wired_source_still_not_verified）；guard_block_rate / drift_event_rate
  的 advisory 仅限"源缺失"分支，源存在但无数据分支保持非 advisory → 驱动 NOT_VERIFIED。
- 测试：test_slo_consistency.py 13 例 + 既有 test_governance_metrics.py /
  test_slo_gate.py 全绿（合跑 158 passed 中覆盖）。

### AC-05（F-06 白名单）— PASS（附 P2 条件）

- 实测全仓库复扫：overall PASS，exit 0；secret 0 findings、injection HIGH 0 / MEDIUM 0、
  permission pass（5 条非高危）、dependency skipped 附原因（修复前 BLOCKED：
  H:1 + secret 7 + injection 26/4）。
- 白名单类别核对（对真实扫描 skipped_files 做类别统计）：仅 5 类
  scanner_self(4) / tests 夹具(123) / seeded_defects(7) / docs(37) / archive(755)，
  无任何非白名单路径被跳过（程序化检查通过）；skipped_files 逐条透明返回。
- SafeLoader 子类识别独立 probe：`class UniqueKeyLoader(yaml.SafeLoader)` +
  `yaml.load(..., Loader=UniqueKeyLoader)` 不报；无 Loader 的 `yaml.load` 仍 HIGH 阻断。
- 真实代码路径独立 probe：os.system / eval / yaml.load(unsafe) → HIGH blocked；
  真实 SQL f-string（SELECT…FROM / UPDATE…SET / DELETE FROM）→ HIGH blocked；
  真实 `el.innerHTML = x` → MEDIUM 两条规则命中。
- 白名单未放行真实代码（真实代码路径零豁免，实测 + 测试 test_real_code_paths_still_reported）。

### AC-06（release check + 全量回归）— PASS（含 2 个预期瞬时失败）

- `release.py check` 实测：version_sync 如实 FAIL（fail-closed，文案含 bump 约定），
  exit 1；slo_gate 步骤独立实测 PASS（releases=1，CONSUMING，decision PASS，
  missing=[]）；compile 68/68（compile-evidence.json status pass）。
- 关键测试文件合跑：**158 passed, 1 failed, 1 skipped**；唯一失败 =
  test_pyproject_version_matches_git_head（pyproject 3.12.39 vs HEAD 3.12.38，预期，
  提交后自愈）。
- 全量回归（`pytest tests/ -q`，3822 collected）：**3744 passed, 2 failed,
  64 skipped, 12 xfailed**（198.78s）。2 个失败均为预期瞬时项：
  ① test_manifest_t0095（HANDOFF 引用 T-0100 evidence-manifest 尚未生成，F-02 同类，
  任务收尾生成清单后自愈）；② test_pyproject_version_matches_git_head（同 key_tests）。
  **无其他意外失败**；相对 T-0099（3698 passed）新增 ~46 例全部通过。

### AC-07（约束零弱化）— PASS 总体（专项结论见第三节）

---

## 二、逐项 findings 复验记录（命令 + 输出摘要）

| Finding | 复验命令 | 输出摘要 | 结论 |
|---------|----------|----------|------|
| F-01 | `python tools/tool_registry_status.py --json`；`…`（文本模式） | exit 0；合法 JSON overall=PASS；文本模式 exit 0 Overall: PASS；stderr 空 | 已修复 |
| F-03 | `python scripts/release.py bump --help` / `bump --to 3.12.39`（幂等） / 10 字段载体校验脚本 | 子命令可用；no-op exit 0；非法版本 exit 2；全部载体 = 3.12.39 | 已修复 |
| F-04 | `python agents/security-engineer/scripts/run_security_scan.py --project-root . --output-dir <tmp>` | dependency=skipped（reason 含 exit=1 + venv traceback 尾行），counts 全零；overall PASS exit 0 | 已修复（语义正确） |
| F-05 | `python tools/loop_metrics.py --report`；预算对比脚本（releases=0/1/3） | status PASS（原 NOT_VERIFIED）；missing 0；advisories 14 项；metrics 与 gate 预算逐字段一致 | 已修复（口径+语义） |
| F-06 | 同上全仓库复扫 + 规则 probe（10 组样例） | secret 0 / injection 0/0；真实 SQL/HTML/yaml/os.system/eval 仍检出；UI 标签/字符串字面量/SafeLoader 子类不误报 | 已修复（含 P2 覆盖缺口，见下） |

---

## 三、约束零弱化专项结论（本报告最重要部分）

### 3.1 slo_gate 门禁判定层：原样，未改

- `loop_core/slo_gate.py` 的 git diff 仅 8 行 **docstring**（release_fee 说明），
  零逻辑改动。`REQUIRED_SOURCES` fail-closed（缺失/不可解析 → BLOCK 列源）、
  FREEZE→BLOCK（ERROR_BUDGET_EXHAUSTED）、CONSUMING→PASS（附警告）、
  exemption/恢复机制、toggle 全部未动（读源码逐函数核对）。
- release_fee 口径统一函数 `release_fee_consumption` 确为 metrics 与 gate **真共用**
  （gate 的 `_compute_gate_budget` → `compute_error_budget` → `release_fee_consumption`；
  无平行实现）。实测两调用点输出逐字段一致。
- 变更只落在**报告呈现层**：`governance_metrics.build_report` 的
  status/advisories/missing 计算与 `tools/loop_metrics.py` CLI 输出（advisories 打印、
  --releases help 口径提示）。门禁裁决路径（slo_gate.py）零触碰。
- 实测 `check_slo_gate('.', releases=1)`：decision PASS、missing=[]；空目录场景
  （tests）仍 BLOCK（数据不足 fail-closed）。

### 3.2 SKIP 是否掩盖真实阻断：不掩盖

- SKIP 仅发生在环境不可用（命令缺失/超时/执行异常/非零退出且输出不可解析/项目类型
  未知）；**均附明确 reason**（工具名 + exit 码 + stderr 尾行），报告 Markdown 显示
  `SKIPPED — <原因>`，JSON 含 skipped/reason 字段。
- 真实 CVE 路径：pip-audit exit=1 + 可解析漏洞 JSON → 计数 HIGH/CRITICAL → blocked
  （测试 + 代码路径 + probe 三重确认）。修复前唯一的行为变化是"非零退出 + 输出不可解析"
  从"合成 HIGH"变为"SKIP+原因"——这正是 F-04 要求的修复本体，不是吞失败。
- 既有 `_reuse_quality_audit` 复用路径语义未变（quality-engineer blocked 仍 blocked）。

### 3.3 SQL/HTML 规则精度修正：放行了两类真实注入形态（P2）

开发者自称"为达成验收意图所需"的两条修正，经独立 probe 验证：

- **真实完整语句仍检出**：`f"SELECT * FROM users WHERE name={kw}"`、
  `f"UPDATE users SET email={e} WHERE id=1"`、`f"DELETE FROM {t} WHERE id={i}"` →
  HIGH blocked（旧规则同）；`el.innerHTML = userInput` → MEDIUM（旧规则同）。
- **两处覆盖回退（旧规则检出、新规则静默）**：
  1. **split-literal SQL 拼接**：`"SELECT " + cols + " FROM " + tbl + " WHERE id=" + uid`
     —— 旧 `+` 规则（HIGH 阻断级）命中，新 `_SQL_STMT` 语句上下文规则不命中。
     这是经典动态 SQL 注入形态，且属于 HIGH 阻断级回退。
  2. **bracket-access HTML sink**：`obj["innerHTML"] = userInput` —— 旧 MEDIUM 规则
     命中，新 `(?<!["'])…(?!["'])` lookaround 将其排除（MEDIUM 非阻断级，但仍是
     DOM XSS 真实 sink）。
- 评估：两条修正把"关键词任意出现"收紧为"语句上下文"，消除 `[loop-update]` 类误报
  是合理的，但收紧幅度超出必要（`+`/`%` 系规则本就要求拼接/格式化运算符，误报面窄），
  造成上述两处真实漏洞形态漏检。**风险等级：可接受但需处理**——放行前按 P2-1/P2-2
  处理（修复或显式接受+测试钉住）。已验证的修复正则（零误报于 UI 标签/字符串字面量）：

  - SQL split-literal（追加到 `+`/`%` 系规则）：
    `["']\s*(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+(?:TABLE|DATABASE|INDEX|SCHEMA|VIEW))\s+[^"']*["']\s*[+%]`
  - HTML bracket sink（追加到 MEDIUM HTML 规则）：
    `\.(?:innerHTML|outerHTML|insertAdjacentHTML)\s*=|\[["'](?:innerHTML|outerHTML|insertAdjacentHTML)["']\]\s*=`

### 3.4 其余 fail-closed 语义逐项核对：无变化

- version_sync：判定逻辑原样（仅文案），实测漂移仍阻断。
- tool_registry_status 退出码 0/1/2 原样（含 guard fail → 2 的回归测试）。
- guard_health / validate_state / compile / key_tests 步骤零改动。
- 白名单仅豁免已验证类别（scanner_self/test_fixture/docs/archive），真实代码路径零豁免
  （skipped_files 类别统计 + probe 双重确认）。

---

## 四、越界改动评估

| 文件 | 判定 | 依据 |
|------|------|------|
| `.zcode-plugin/plugin.json`（version 3.12.36→3.12.39 单字段） | **必要越界，可接受** | 不在 T-0100.md allowed_paths 字面清单，但 `tests/test_version_consistency.py::test_plugin_json_version`（第 57-64 行）**强制校验**该文件 version == pyproject；不更新则 AC-01/AC-06 无法达成。改动仅单行 version，且在 f-03.md/commands.md 中如实记录 |
| `.ai/*`（HANDOFF/state/task_graph/gates/project_continuity/T-0099 status/observability 证据/conformance 时间戳） | 范围内（.ai/ 在 allowed_paths） | 全部为治理投影/生成产物；guard-events.jsonl 仅追加（+320/-0）；metrics-report 为 F-05 修复后真实再生成 |
| `README.md` / `docs/06-delivery.md` / `CHANGELOG.md`（含 v3.12.37/v3.12.38 补录条目） | 范围内 | 版本载体（测试强制），条目内容与提交历史一致 |
| `hooks/` | 无改动 | — |
| 业务源码（src/ 除版本号） | 无改动 | src/loop_engine/__init__.py 仅 __version__ |

结论：无超出 IN SCOPE 的实质改动；plugin.json 为测试强制载体的必要越界，记录透明，
建议主会话在后续任务 allowed_paths 中补入该路径（P3 流程建议）。

---

## 五、观察项（P3，不阻断）

1. `bump --dry-run`（子命令后置标志）不支持（argparse 报错 exit 2）；全局形式
   `--dry-run bump --to x` 可用。与 check 的"两种写法兼容"处理不一致——建议 bump
   也加 `--dry-run` 子参数（一行改动）。
2. pip-audit 部分漏洞 severity 为 CVSS 向量字符串（如 "CVSS:3.1/AV:N/..."），
   `(severity).upper() in counts` 不计入 HIGH/CRITICAL → 可能漏计真实高危。
   **预存限制**（旧版同样代码，非 T-0100 回归），可另开任务修复。
3. `WAVE2_UNWIRED_SOURCES` / `UNWIRED_SLI_IDS` 为常量集合；wave-2 源真正接线后
   必须移除对应条目（test_unwired_source_constants_complete 钉住当前集合，届时需同步
   更新测试）。未接线源"存在但不可解析"与"缺失"同归 advisory（与契约一致，
   接线后需重新审视）。
4. `UNWIRED_SLI_IDS` 中 4 个"尚未记录"SLI 的 advisory 标志在计算分支中恒为 True
   （这些 SLI 无计算分支），标志仅用于 NOT_AVAILABLE 过滤，无实际副作用。

---

## 六、证据与测试清单

- 关键测试合跑：`pytest tests/test_release_bump.py tests/test_tool_registry_status.py
  tests/test_slo_consistency.py tests/test_security_dependency_scan.py
  tests/test_security_scan_whitelist.py tests/test_release.py
  tests/test_version_consistency.py tests/test_governance_metrics.py
  tests/test_slo_gate.py -q` → **158 passed, 1 failed（预期 HEAD 同步）, 1 skipped**
- 全量：`pytest tests/ -q` → **3744 passed, 2 failed（均为预期瞬时项）, 64 skipped,
  12 xfailed**，198.78s
- 本审查复验产物：`/tmp/reg.json`（--json 输出）、`/tmp/t0100-sec-scan/`（真实复扫
  报告）、`/tmp/budget_cmp.py`（口径对比）、`/tmp/probe_fix.py`（规则 probe 与修复
  正则验证）、`/tmp/full_pytest.log`（全量日志）
- 第二轮（P2 复验）产物：`/tmp/t0100_p2_probe.py`（10 组样例端到端 probe，10/10 PASS）
