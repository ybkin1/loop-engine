# T-0098 (D8) 发布/产物体系 — 设计证据

- 任务: T-0098 — D8 发布/产物体系（StaffDeck D8 对标）
- 实现: `scripts/release.py` + 版本同步 + `tests/test_release.py`
- 日期: 2026-08-02
- 状态: implemented（release 决策为候选，GO 需用户另行批准）

## 1. 背景与目标

发布/产物体系缺失：pyproject.toml version=3.11.2 与 git 实际版本 v3.12.36 漂移、
CHANGELOG.md 停在 v3.4.0、无 release 证据目录（.ai/evidence/release/ 不存在）。

目标（对应验收）:

| AC | 内容 | 落地 |
|----|------|------|
| AC-01 | 版本同步 | pyproject/git/CHANGELOG/一致性测试全绿 |
| AC-02 | 构建产物 | wheel+sdist + 产物清单 + SHA256 校验和可复验 |
| AC-03 | release 流程 | 质量门前置阻断 + 证据三件套 + --dry-run 不落盘 |
| AC-04 | 冒烟安装 | 临时 venv 安装 wheel → import；环境不可用 → SKIP 明确标记 |
| AC-05 | 全量回归 | 全量测试无回归（>=3675 passed） |
| AC-06 | 约束不弱化 | 仅新增治理脚本/测试/证据，不改业务语义 |

## 2. 版本同步策略

- **单一事实来源**: pyproject.toml `version`。test_version_consistency.py 从
  pyproject 读取并校验 README.md / src/loop_engine/__init__.py /
  .zcode-plugin/plugin.json / .ai/version-manifest.yaml / docs/06-delivery.md。
- **git 版本来源**: 项目无 git tag，版本号以提交信息头部 `vX.Y.Z` 为准
  （`git log -1 --format=%s` 正则提取），当前 HEAD=v3.12.36（bc6680f）。
- 同步动作：pyproject 3.11.2 → 3.12.36；其余版本载体同步；CHANGELOG 补
  v3.12.25~v3.12.36 共 12 条（主题/AC 摘要来自 git log 提交信息 + 任务文件用户目标）；
  .ai/version-manifest.yaml 新增 3.12.36 快照（历史快照不修改，保留审计轨迹）。
- test_version_consistency.py 扩展 `test_changelog_latest_matches_pyproject`
  （CHANGELOG 最新条目 == pyproject 版本）。

## 3. 构建产物（scripts/release.py build / manifest）

- 构建: `python -m build --outdir dist/` 生成 wheel + sdist。
  - 构建工具缺失（无 `build` 模块）→ 明确报错（提示 `pip install build`）。
  - 隔离构建环境不可用（本机 Python 缺 venv 模块）→ 自动回退
    `--no-isolation`（用当前环境 setuptools），两种模式均实测通过。
- 包内容显式锁定（pyproject `[tool.setuptools]`）:
  - `package-dir = {"" = "src", "loop_core" = "loop_core"}`
  - `packages = ["loop_engine", "loop_core", "loop_core.llm"]`
  - 原因：仓库存在顶层遗留 `loop_engine/`（flat-layout 时代的
    adapters/cost_tracker 等，未被任何代码导入），与 src/loop_engine 同名；
    自动发现会把 scripts/ 等治理资产打进 wheel。显式锁定后 wheel 仅含
    loop_engine + loop_core + loop_core.llm（已用 zipfile 实测验证）。
- 清单: `dist/release-manifest.json`（schema_version / version / git_commit /
  generated_at / artifacts[]: name/path/sha256/size_bytes）+ `dist/SHA256SUMS`
  （`sha256  filename` 行式，兼容 sha256sum 工具复验）。
  *独立审查修复（P2）*：SHA256SUMS 以 bytes/LF 写入（write_text 默认在
  Windows 会产出 CRLF，导致 `sha256sum -c` 失败）；测试断言文件中无 CR。
- 校验和可复验: 测试重算 sha256 与清单逐项比对。

## 4. release 流程（质量门前置 → 构建 → 证据）

`release` = check → build → manifest → 证据落盘；任一前置失败即阻断（退出码 1），
不构建、不落盘（fail-closed，与项目约束语义一致）。

质量门前置（check）6 步:
1. version_sync — pyproject == git HEAD 版本（防漂移发布）
2. validate_state — **调用真实校验器** `.zcode/tools/validate_state.py`
   （subprocess，超时 120s，输出截断；退出码非 0 / 超时 / 缺失 → 阻断）。
   *独立审查修复（P1-1）*：原轻量实现仅 YAML 可解析 + version-manifest 一致，
   对连续性漂移等盲视；现直接运行真实校验器（state/task/待决门禁/治理不变量/
   ProjectContinuity/handoff/角色合同全量检查），fail-closed 不放松语义。
3. compile — compileall 运行时代码目录（loop_core/src/scripts/hooks/tools）
4. guard_health — loop_core.guard_health GuardHealth.summary() 必须 PASS
   （BROKEN/DORMANT 任一 → FAIL；实测 5 个 guard 全部存活）
5. slo_gate — **独立审查增补（P1-1）**：调 `loop_core.slo_gate.check_slo_gate`
   （releases=1，本次发布的 release_fee 计入预算）。budget HEALTHY/CONSUMING →
   PASS（CONSUMING 附警告）；FREEZE / 数据不足（fail-closed）/ 异常 → FAIL。
   只新增阻断条件，不放松任何门禁语义（T-0093 AC-06 姿态延续）。
6. key_tests — pytest 子集 test_version_consistency + test_loop_core

> **check 决策（独立审查，P1-1）**：reviewer 建议"check 增补全量测试与 SLO
> 检查，或任务文档明确降级理由"。决策：**增补 SLO 检查到 check**（轻量，
> 单步调 check_slo_gate，实测 PASS）；**全量测试保持子集**——理由：check 是
> 发布前快速门（秒级），全量测试（~3700 项）在 CI/验收阶段已跑
> （AC-05 全量回归），不重复承担；key_tests 子集聚焦版本一致性与核心包，
> 与发布动作直接相关。

> 注：compile 门禁首次运行即发现并修复了 HEAD 中预存语法错误
> （scripts/role_checkers/review_coverage_checker.py 第 9 行字符串内裸换行）——
> 这正是质量门前置存在的意义（T-0082 "guard 可以静默死亡"教训的发布侧对应）。

release 证据三件套（.ai/evidence/release/<version>/）:
- `release-decision.request.json` — **候选**决策（version/task_id/owners/deadline/
  status=requested/requested_at/decision=null）。不写 release_decision.json，
  避免与 S6 门禁的 check_delivery_gate_evidence 语义冲突——真实 GO/NOGO 由
  用户/delivery-manager 决策后写入 release_decision.json。
- `release-manifest.json` — 与 dist/ 同源（复制）
- `SHA256SUMS` — 同上

`--dry-run`: 全子命令支持，只打印计划（步骤/产物/落盘路径），不执行不落盘
（测试断言 dist/ 与 .ai/ 均不被创建）。

## 5. 冒烟安装（smoke）

- 临时 venv（tempfile.mkdtemp）→ `python -m venv` → `pip install dist/*.whl`
  （优先全依赖；失败回退 --no-deps）→ import loop_engine/loop_core →
  `__version__` 与 pyproject 版本比对。
- 环境不可用（venv 创建失败 / venv 内无 pip / 无法调用）→ **SKIP 明确标记**
  （status=SKIP + 原因），不阻断 release 流程本身；CLI 退出码 0，日志清晰。
- 本机环境实测: C:\Python312 以 safe_path 构建且无 venv 模块 → venv 路径
  SKIP（预期标记）；等价真实安装验证由 `pip install --target` + 代码内
  sys.path 注入完成（wheel 安装 → import 版本一致，实测 PASS）。
- 测试覆盖: 真实 venv 路径（有环境则跑）+ 脚本化 mock 路径（PASS/SKIP 分支
  确定性覆盖）+ venv-less 真实安装路径。

## 6. 约束与安全

- 未执行真实发布/上传；未写 release_decision.json（GO 需用户决策）。
- 未弱化任何激活约束；新增内容均为治理侧（scripts/tests/证据）。
- dist/、*.egg-info/、build/ 已在 .gitignore（dist/ 产物不提交 git，已核实）。
- 遗留根级 loop_engine/ 包未被改动（不在本次分发范围，亦未被任何代码导入）。

## 7. 证据索引

- 代码: scripts/release.py（check/build/manifest/release/smoke）
- 测试: tests/test_release.py（AC-01~04 + 复审修复用例，实测 29 passed
  + 1 SKIP(环境)）
- 版本: pyproject.toml/CHANGELOG.md/.ai/version-manifest.yaml（3.12.36）
- 产物: dist/（wheel + sdist + release-manifest.json + SHA256SUMS，gitignored）
- release 证据: .ai/evidence/release/3.12.36/（三件套）

## 8. 独立审查放行条件修复（2026-07-31，CONDITIONAL_GO）

| 项 | 修复 | 验证 |
|----|------|------|
| P1-1a | `step_validate_state` 改调真实校验器 `.zcode/tools/validate_state.py`（subprocess，timeout=120s，输出截断；退出码非 0 / 超时 / 缺失 / 无法启动 → fail-closed 阻断） | 真实损坏 state.yaml → 校验器 exit≠0 → step 阻断（实测）；单测覆盖调用/非0/超时/缺失四分支 |
| P1-1b | check 增补 `step_slo_gate`（调 `loop_core.slo_gate.check_slo_gate`，releases=1） | 实测 PASS（CONSUMING，剩余 95/100）；单测覆盖 PASS/BLOCK + cmd_check 阻断 |
| P1-1c | 决策：全量测试保持子集（check 为快速门，全量在 CI/验收已跑），SLO 检查增补入 check（见 §4 决策注） | design.md §4 明示理由 |
| P1-2 | `tests/test_release.py` `built_dist` fixture 隔离到 pytest 临时目录（tmp_path_factory），不再改写真实 dist/ | 测试运行前后 dist/ 内容不变（CRLF 旧产物未被重写，实测） |
| P2 | `write_manifest` 的 SHA256SUMS 改 bytes 写入（LF 保持，兼容 `sha256sum -c`） | 单测断言无 CR；`sha256sum -c` 逐项复验通过 |

约束核对：未改业务源码（loop_core/ 仅 slo_gate 被调用，未修改）；未伪造校验和
（证据由真实构建产物重算）；未放松任何门禁语义（check 由 5 步增至 6 步，只增
阻断条件）。
