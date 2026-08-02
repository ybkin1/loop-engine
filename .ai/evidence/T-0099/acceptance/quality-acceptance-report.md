# Loop 工程质量验收报告 — T-0099（四组全能力端到端验收）

- 任务：T-0099（G-T-0099-REQUIREMENTS，approved）— Loop 工程自身质量验收
- 角色：quality-engineer（只验收与写证据，不修复）
- 执行时间：2026-08-02 02:35 ~ 02:46 (UTC+0)
- 环境：Windows 10 x64 / Git Bash / Python 3.12.10（C:/Python312/python.exe）
- 版本信息：
  - git HEAD：`31c3c2d44471e68034634a27d9dafa008ed986f4`（subject: `v3.12.37: T-0098 — D8 发布/产物体系（版本同步 3.12.36 + wheel/sdist + release 流程 + 冒烟，6/6 AC GO）`）
  - pyproject.toml version：`3.12.36`（版本单一事实来源；`.ai/version-manifest.yaml` 仅为旧设计遗留的版本投影产物（T-0098 生成，内容与 pyproject 一致），不作为独立事实来源）

---

## 组 1：静态门禁（AC-01）

| # | 验收项 | 标准 | 结果 | 证据路径 | 备注 |
|---|--------|------|------|----------|------|
| G1-1 | validate_state.py | `[ok] state is usable` | **PASS** | `quality/g1-1-state-validate.txt` | 输出 `[ok] state is usable`，exit 0 |
| G1-2 | compile_gate | pass，68 文件全编译 | **PASS** | `quality/compile-evidence.json` | compiled 68/68，failed 0，status pass |
| G1-3 | test_version_consistency | 全过 | **PASS** | `quality/g1-3-version-consistency.txt` | 7/7 passed in 0.33s |
| G1-4 | tool_registry_status | missing 0 / drift 0 | **PASS*** | `quality/g1-4-registry-status.json` | 数据 missing:[] drift:[] overall PASS；但 `--json` 模式因工具缺陷（UnboundLocalError 'death'）退出码=1（见 F-01）；文本模式 exit 0 |
| G1-5 | loop_guard_health | guard 5/5 ALIVE | **PASS** | `quality/g1-5-guard-health.json` | 5 ALIVE / 0 DORMANT / 0 BROKEN，overall PASS |

**组 1 汇总：5 项中 4 PASS、1 PASS*（G1-4 数据达标但 CLI 退出码有缺陷，记 F-01）。**

## 组 2：动态质量（AC-02）

| # | 验收项 | 标准 | 结果 | 证据路径 | 备注 |
|---|--------|------|------|----------|------|
| G2-6 | 全量 pytest | 0 failed | **FAIL** | `quality/g2-6-full-suite.txt` | **2 failed, 3698 passed, 64 skipped, 12 xfailed**（291.87s）：① test_manifest_t0095 HANDOFF 引用 T-0099 未生成清单（瞬时态，见 F-02）；② test_release 版本漂移 pyproject=3.12.36 vs git HEAD=3.12.37（真实漂移，见 F-03） |
| G2-7 | tool_eval | 内置样例全过 | **PASS** | `quality/eval-report.json` + `quality/g2-7-eval-stdout.txt` | loop-agent-eval v1 6 cases：PASS 6 / FAIL 0 / SKIP 0 |
| G2-8 | vertical_slice conformance | gate PASS | **PASS** | `quality/g2-8-vertical-slice.txt` | contract_planes 37/37 + test_vertical_slice 86/86 |

**组 2 汇总：3 项中 2 PASS、1 FAIL（2/3700 用例失败，其中 1 项为瞬时任务态、1 项为真实版本漂移）。**

## 组 3：治理质量（AC-03）

| # | 验收项 | 标准 | 结果 | 证据路径 | 备注 |
|---|--------|------|------|----------|------|
| G3-9 | loop_metrics | HEALTHY 或明确记录 | **PASS*** | `quality/g3-9-metrics-stdout.txt`；报告本体 `.ai/evidence/observability/metrics-report.json/.md` | error budget HEALTHY（remaining 100.0/100.0），但 status=NOT_VERIFIED，14 个数据源缺失（见 F-05）；与 slo_gate 的 consumed 5.0 口径不一致 |
| G3-10 | second_failure_checker | 无未解决（或 DISABLED 明确记录） | **PASS** | `quality/g3-10-second-failure.json` | decision PASS，status_detail=DISABLED（opt-in 配置未启用，advisory-only），exit 0，无 blocking |
| G3-11 | 安全扫描 | 无阻断级 | **FAIL** | `quality/security-scan/security_report.json` + `security_summary.md` + `g3-11-security-notes.md` | verdict=BLOCKED（exit 2）：dependency_scan blocked（pip-audit 环境崩溃 → 失败关闭合成 HIGH:1，无确认 CVE，见 F-04）；secret_scan 7 条（均为测试夹具/文档示例/占位符）；injection_scan HIGH:26/MEDIUM:4（扫描器自指规则表 + 测试夹具 + 误报，见 F-06）；permission_audit pass |
| G3-12 | loop_self_audit --quick | 规则式全过 | **PASS** | `quality/g3-12-self-audit.json` | overall PASS，failed: [] |

**组 3 汇总：4 项中 2 PASS、1 PASS*（带 caveat）、1 FAIL（BLOCKED 由扫描器设计与环境导致，未确认真实漏洞）。**

## 组 4：发布就绪（AC-04）

| # | 验收项 | 标准 | 结果 | 证据路径 | 备注 |
|---|--------|------|------|----------|------|
| G4-13 | release.py check | 6 步全 PASS | **FAIL** | `quality/g4-13-release-check.txt` + `quality/release-check-steps.json` | 第 1 步 version_sync FAIL 即阻断（fail-closed 行为正确，成功拦截真实漂移）。逐步隔离实测：version_sync FAIL（3.12.36 vs 3.12.37，F-03）；validate_state / compile / guard_health(5/5) / slo_gate（consumed 5.0/100.0，remaining 95.0）/ key_tests 5 项 PASS → **5/6 PASS，1 FAIL** |

**组 4 汇总：1 项 FAIL（发布被正确阻断，根因 F-03 版本漂移）。**

---

## 分组汇总

| 组 | 验收项数 | PASS | PASS*（带 caveat） | FAIL | 关键结论 |
|----|---------|------|------|------|----------|
| 组1 静态门禁 | 5 | 4 | 1 | 0 | 全部门禁可运行且状态健康；G1-4 CLI 缺陷 |
| 组2 动态质量 | 3 | 2 | 0 | 1 | 3698/3700 通过；2 失败各有所归 |
| 组3 治理质量 | 4 | 2 | 1 | 1 | 安全扫描 BLOCKED 无确认漏洞；SLO 不可验证 |
| 组4 发布就绪 | 1 | 0 | 0 | 1 | 发布被版本漂移正确阻断 |
| **合计** | **13** | **8** | **2** | **3** | |

注：PASS* 表示标准数据达标但存在记录在案的 caveat（G1-4 工具缺陷、G3-9 数据源缺失）；汇总表按逐项标记单列计数（不计入 PASS 列），验收上视为通过并附 findings。

---

## Findings 清单（只记录，不修复）

| ID | 级别 | 位置 | 描述 | 影响 |
|----|------|------|------|------|
| F-01 | P2 | `tools/tool_registry_status.py:82` | `--json` 模式下局部变量 `death` 未绑定（仅文本分支 line 63 赋值），打印完合法 JSON 后必崩 `UnboundLocalError`，健康状态也退出码 1；文本模式正常 | 自动化调用 `--json` 的健康检查会被误判为失败；证据 `g1-4-registry-status.json` |
| F-02 | P3 | `tests/test_manifest_t0095.py:32-42` | 测试锁定 T-0095 清单，却扫描 HANDOFF.md 中**全部** evidence-manifest 引用；进行中任务（如 T-0099）的 HANDOFF 引用其尚未生成的清单 → 测试变红 | 当前全量测试 2 失败之一；T-0099 证据清单生成后自愈；建议后续将扫描限定到本任务条目（不修复，仅记录） |
| F-03 | **P1** | git HEAD 提交信息 vs `pyproject.toml` | 版本漂移：pyproject.toml=3.12.36（.ai/version-manifest.yaml 投影一致，非独立事实来源），而 T-0098 提交 subject 前缀为 `v3.12.37`（"版本同步 3.12.36" 之后未改 subject）→ `scripts/release.py` 的 git_head_version 解析出 3.12.37 | 阻断 release.py check 第 1 步（发布冻结，fail-closed 正确触发）；test_release.py 版本同步用例失败；不修复则无法发布 |
| F-04 | P2 | 环境（Python 3.12 安装缺 stdlib `venv`） | `pip-audit` 直接崩溃（证据主体为崩溃 traceback：`ModuleNotFoundError: No module named 'venv'`；退出码以实测为准，复测 `pip-audit -r requirements.txt --format json` 退出码=1），依赖 CVE 无法本地验证；requirements.txt 仅 PyYAML>=6.0 | dependency_scan 无法证明零已知 CVE（扫描器失败关闭合成 HIGH:1）→ 安全扫描 BLOCKED 的主因之一 |
| F-05 | P2 | `tools/loop_metrics.py` / `.ai/ledger/` | 14 个观测数据源缺失（phase_transitions.jsonl、guard_decisions.jsonl、runtime-events.jsonl、drift/guard_block 等 SLI）→ metrics status=NOT_VERIFIED，error budget 100/100 未经真实数据验证；且与 release slo_gate（consumed 5.0/remaining 95.0）口径不一致 | SLO/error budget 状态不可信（可能偏乐观）；建议补齐 ledger 数据源后复验 |
| F-06 | P3 | `agents/security-engineer/scripts/run_security_scan.py` + `scripts/security_scan.py` | 注入扫描器无自排除/白名单：命中自身正则规则表（如 security_scan.py:42-47）、测试夹具、seeded_defects 故意缺陷样本、`yaml.load(..., Loader=UniqueKeyLoader)`（SafeLoader 子类，安全）；secret 扫描命中占位符/文档示例 | 26 HIGH + 7 secret 全为误报/夹具，verdict BLOCKED 由设计所致；建议加 allowlist/来源分类（不修复，仅记录） |

无 P0 项。已确认未发现业务源码中的可利用漏洞与损坏机制。

---

## 验收裁决建议：CONDITIONAL_GO

Loop 工程自身的四组能力全部可执行、机制有效（守卫 5/5、编译 68/68、门禁 fail-closed 行为在真实漂移下正确触发、安全扫描与发布检查均如实报告），3698/3700 用例通过。但发布就绪（AC-04）与全量测试（AC-02）未达 GO 标准，根因集中在 F-03 版本漂移（真实缺陷）与 F-02 瞬时态。故裁决 **CONDITIONAL_GO**，附条件：

1. **（必要条件）解决 F-03**：对齐版本事实来源（pyproject=3.12.36，git HEAD subject 应同步）后，`release.py check` 6 步须全 PASS；
2. **F-02**：T-0099 证据清单（evidence-manifest.v1.yaml）生成后全量测试须 0 failed（或修正该测试的引用扫描范围）；
3. **F-01**：修复 tool_registry_status `--json` 退出码缺陷后复跑（或验收期以文本模式为准）；
4. **F-05**：补齐 ledger 观测数据源，令 loop_metrics 达到 VERIFIED（error budget 才可信）；
5. **F-04/F-06**：恢复 pip-audit 可用环境（补齐 venv 模块）并为扫描器配置误报白名单后复扫，期望 verdict PASS。

若 F-03 无法在近期解决（发布冻结持续），可降级为 NO-GO（发布不可行，但工程自身运行与治理不受阻）。

---

## 证据文件清单

- `.ai/evidence/T-0099/quality/compile-evidence.json`（工具生成）
- `.ai/evidence/T-0099/quality/eval-report.json`（工具生成）
- `.ai/evidence/T-0099/quality/release-check-steps.json`（逐步隔离实测）
- `.ai/evidence/T-0099/quality/g1-1-state-validate.txt`
- `.ai/evidence/T-0099/quality/g1-3-version-consistency.txt`
- `.ai/evidence/T-0099/quality/g1-4-registry-status.json`
- `.ai/evidence/T-0099/quality/g1-5-guard-health.json`
- `.ai/evidence/T-0099/quality/g2-6-full-suite.txt`
- `.ai/evidence/T-0099/quality/g2-7-eval-stdout.txt`
- `.ai/evidence/T-0099/quality/g2-8-vertical-slice.txt`
- `.ai/evidence/T-0099/quality/g3-9-metrics-stdout.txt`
- `.ai/evidence/T-0099/quality/g3-10-second-failure.json`
- `.ai/evidence/T-0099/quality/g3-11-security-notes.md`
- `.ai/evidence/T-0099/quality/g3-12-self-audit.json`
- `.ai/evidence/T-0099/quality/g4-13-release-check.txt`
- `.ai/evidence/T-0099/quality/security-scan/security_report.json` + `security_summary.md`（工具生成）
- `.ai/evidence/observability/metrics-report.json` / `metrics-report.md`（工具生成）
- `.ai/evidence/observability/dashboard-snapshot.md` / `.html`（工具生成，已更新）
