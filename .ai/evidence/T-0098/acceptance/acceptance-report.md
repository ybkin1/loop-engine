# T-0098 验收报告（acceptance-report）

> **T-0098: D8 发布/产物体系 | 2026-08-02**
> Gate: G-T-0098-REQUIREMENTS（user 批准："D8 发布产物体系"）
> 独立审查：CONDITIONAL_GO（范围偏差判定合理必要）→ 放行条件全部修复 → GO

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 版本同步（pyproject/git/CHANGELOG + 一致性测试） | ✅ PASS | pyproject 3.12.36 == git HEAD；CHANGELOG 12 条降序；test_version_consistency 7/7（载体同步为既有测试强制要求，审查判定合理必要） |
| AC-02 | 构建产物（wheel/sdist + 清单 + 校验和可复验） | ✅ PASS | 真实构建 wheel+sdist（setuptools 显式锁定仅含核心包）；sha256sum -c 2/2 OK；双 manifest 逐项一致；dry-run 不落盘 |
| AC-03 | release 流程（质量门前置 + 证据结构 + dry-run） | ✅ PASS | check 6 步（validate_state 走真实校验器 + SLO 门禁）；失败阻断；三件套结构正确（requested 候选）；dry-run 零写入 |
| AC-04 | 冒烟安装（临时 venv；SKIP 明确标记） | ✅ PASS | 环境无 venv → 如实 SKIP + 原因；--target 等价真实安装 PASS（import + 版本一致） |
| AC-05 | 全量测试无回归 | ✅ PASS | 3700 passed / 64 skipped / 12 xfailed / 0 failed（基线 3675 +25） |
| AC-06 | 无约束弱化 + 不执行真实发布 | ✅ PASS | hooks/.zcode 零改动；review_coverage_checker 为真实语法错误修复（HEAD 预存）；request 候选不触发发布；无上传代码 |

## 交付物清单

1. `scripts/release.py`（check/build/manifest/release/smoke + dry-run）
2. 版本同步：pyproject.toml + CHANGELOG.md + 6 个版本载体 + [tool.setuptools] 锁定
3. `tests/test_release.py`（19+8 测试）+ test_version_consistency 增补
4. `.ai/evidence/release/3.12.36/`（release-decision.request.json + release-manifest.json + SHA256SUMS）
5. `.ai/evidence/T-0098/`：approval/execution/compile-evidence + release/design.md + evidence-manifest + commands + acceptance
6. 预存语法错误修复（review_coverage_checker.py）

## 治理记录

- 版本漂移修复（3.11.2 → 3.12.36，CHANGELOG v3.4.0 → v3.12.36）
- 范围偏差（版本载体同步）经独立审查判定合理必要（既有测试强制要求，删测试才是弱化）
- 放行条件 3 项全部修复（真实校验器接入 / 证据重生成 / CRLF）
- 全程零越界写入（偏差项审查确认）；无真实发布动作

## 最终裁决

**GO**（CONDITIONAL_GO 放行条件全部修复；6/6 AC 达成）

## 已知遗留（P3，记录）

- manifest path 平台相关（Windows 反斜杠）；smoke 单 wheel；dynamic repair 不覆盖 version-manifest 的系统性缺口（建议后续任务）
- 本机无 venv 模块（smoke SKIP，--target 等价验证）
