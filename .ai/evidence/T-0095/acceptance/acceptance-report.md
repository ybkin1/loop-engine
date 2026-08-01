# T-0095 验收报告（acceptance-report）

> **T-0095: 遗留清理包 — P3 技术遗留系统性清理 | 2026-08-02**
> Gate: G-T-0095-REQUIREMENTS（user 批量批准："批准T-0095、96、97"）
> 独立审查：CONDITIONAL_GO（7/7 AC，写入拦截零放宽）→ P1 修复 → [ok] state is usable

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 死导入清理 | ✅ PASS | capability_registry field 删除；ruff F401 目标文件 0 命中 |
| AC-02 | slo.yaml 显式化 | ✅ PASS | 14 条 SLI 与 B2 内置逐字段一致 + fail-closed 校验（9 类非法配置拒绝）+ 门禁读取生效（HEALTHY exit 0） |
| AC-03 | guard-events 轮转 | ✅ PASS | 行数/字节双阈值 + 归档链 + 事件不丢 + 失败静默；5 测试 |
| AC-04 | env 链统一 | ✅ PASS | KEY_TIERS 规范表（ENV_TIERS 同一对象）+ resolve_api_base_url；6 测试 |
| AC-05 | 引用边界/metrics 顶层/SLO 去重 | ✅ PASS | 双前缀修复（测试抓到首版缺陷）；顶层非对象 NOT_AVAILABLE；单次开关检查；9 测试 |
| AC-06 | 全量测试无回归 | ✅ PASS | 3521 passed / 63 skipped / 12 xfailed / 0 failed（基线 3476 +45） |
| AC-07 | 无约束被弱化 | ✅ PASS | 豁免口径统一为等价谓词（逐行 diff 确认零放宽）；全链 104 passed |

## 交付物清单

1. 10 项清理（源码 14 文件 + slo.yaml + evidence-manifest）+ 43 项新测试
2. `.ai/evidence/T-0095/`：approval/execution/compile-evidence + cleanup/design.md + evidence-manifest.v1.yaml + commands + acceptance

## 治理记录

- 批量登记批次第 1 项；YAML_DUPLICATE_KEY 修复（T-0094 尾部块归位）
- P1 修复：HANDOFF 结构化块重建（manifest 创建后）→ [ok] state is usable
- 全程零越界写入；写入拦截零放宽（逐行 diff 审查）

## 最终裁决

**GO**（CONDITIONAL_GO 的 P1 已修复；7/7 AC 达成）

## 已知遗留（归档记录）

- Bash 反斜杠路径 shlex tokenizer；粘性 loop_mode 语义；dev.py POSIX 验证；未知任务 id 边语义
- hooks 两文件 11 处既有 F401（本次零引入）
