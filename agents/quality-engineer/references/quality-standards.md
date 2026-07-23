# 质量门标准参考——各语言/框架的门槛依据

本文为质量工程师 agent 的判断提供标准依据。各门槛值的设定原则：
- **不追求 100% 覆盖率。** 80% 是业界公认的"高置信度"阈值——
  低于 80% 的模块在变更时回归 bug 率显著上升（来源：IEEE 多项目元分析，2023）。
- **lint 零容忍。** Lint 检查的是确定性错误（未使用变量、语法歧义、已知反模式），
  非零意味着代码包含已知不良实践。
- **HIGH/CRITICAL CVE 零容忍。** MODERATE 及以下可根据项目场景和管理员决策接受。

## Python 项目

| 工具 | 推荐命令 | 门槛 |
|---|---|---|
| Lint | `ruff check --output-format json .` | 0 |
| Typecheck | `mypy --strict src/` | 0 errors |
| Test | `pytest --cov=src --cov-report=term -q` | 全通过 + cov ≥ 80% |
| Audit | `pip-audit -r requirements.txt --format json` | 0 HIGH, 0 CRITICAL |

## JavaScript/TypeScript 项目

| 工具 | 推荐命令 | 门槛 |
|---|---|---|
| Lint | `eslint src/ --format json` | 0 |
| Typecheck | `tsc --noEmit` | 0 errors |
| Test | `vitest run --coverage` | 全通过 + cov ≥ 80% |
| Audit | `npm audit --json` | 0 HIGH, 0 CRITICAL |
| Build | `npm run build` | exit 0 |

## 门槛调整指南

以下情况可以考虑降低门槛（需项目经理在 config.yaml 中显式修改）：
- 项目早期原型阶段：coverage 可降至 60%
- 包含大量自动生成的代码：该目录应在 coverage 配置中排除，而非降低整体门槛
- 遗留代码迁移项目：lint 门槛可暂时设为 N（现有 error 数），每迭代降低直到 0

## 不接受的调整理由

以下理由不会被质量工程师接受（数字不变，门槛不改）：
- "时间不够"
- "这个函数很简单"
- "之前也没测"
- "AI 生成的我看了，没问题"
