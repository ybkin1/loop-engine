# T-0117 契约差异表与收敛方案（contract-unification）

## 1. 双实现现状（T-0109 遗留 #3 收敛前）

| 维度 | loop_core/security_scanner.py | agents/security-engineer/scripts/run_security_scan.py |
|------|------------------------------|------------------------------------------------------|
| 定位 | 进程内库（正则扫描 5 组 SS-001~SS-030） | CLI 编排（4 类：依赖 CVE/密钥/注入/权限审计） |
| 输出 | `SecurityReport.to_dict()`（无顶层 schema） | `security_report/v1`（schema/role/timestamp/project/scans/overall/blocked_by）+ 每 scan findings_contract |
| 退出码 | 无 CLI | EXIT_PASS=0 / EXIT_BLOCK=2 |
| 判定 | critical→BLOCKED / high→FAIL / 其余 PASS | 任一 scan blocked → BLOCKED（overall） |
| 排除 | 整类排除（tests/archive/demo） | 路径白名单分类（skipped_files 透明） |
| 调用方 | quality-engineer run_quality_gates / loop_self_audit / tests | tools/server.py `_run_security_scan` 子进程（MCP security_scan_run 契约） |

## 2. 收敛决策

- **输出契约标准**：`security_report/v1`（run_security_scan.py 既有结构，MCP 消费方）。
- **单一 schema 定义**：schema 常量 + v1 构建器 + 校验器收敛到 `loop_core/security_scanner.py`
  （allowed_paths 内单文件承载，不新建模块）；run_security_scan.py 改引共享构建器。
- **loop_core 侧补 CLI**：`python -m loop_core.security_scanner --project-root/--output-dir/--json`，
  退出码 0/2（PASS/BLOCKED，fail-closed：critical/high 均 exit 2）。
- **add-only 兼容**：`SecurityReport.to_dict()` 保持不变（既有消费方零破坏）；
  新增 `to_v1_report()` 呈现层视图。
- **MCP 契约硬约束**：`tools/server.py` `_run_security_scan` 子进程调用与
  security_report.json 结构不变（build_v1_report 输出字段与 generate_report 原输出逐字段一致）。
- **findings_contract（T-0108 F7）**：两处各自 attach 逻辑保留，语义不变。

## 3. 修改面

| 文件 | 修改 |
|------|------|
| loop_core/security_scanner.py | +SECURITY_REPORT_V1_SCHEMA/build_v1_report/validate_v1_report/to_v1_report/CLI main（add-only，扫描逻辑零改动） |
| agents/security-engineer/scripts/run_security_scan.py | +项目根 sys.path 注入 + 改引 build_v1_report（generate_report 输出逐字段等价）+ SCANNER_SELF_FILES 清 2 条已删路径（T-0113 P3-5） |
| tools/server.py | 零改动（契约兼容验证） |
| tests/test_t0117_contract_unification.py | 新增契约测试（v1 结构/单一 schema 断言/CLI 退出码/SCANNER_SELF_FILES 无残留/既有输出等价） |

## 4. 退出码与判定统一口径

- loop_core CLI：critical>0 或 high>0 → **exit 2**（BLOCKED）；否则 **exit 0**（PASS）。
- run_security_scan：任一 scan status=blocked → **exit 2**；否则 **exit 0**（不变）。
- 语义对齐说明：loop_core 的 Verdict.FAIL（high）在 CLI 层映射 exit 2（fail-closed，
  与 run_security_scan 的 blocked→2 同级语义）。

## 5. 验收映射（任务卡 AC）

- AC-01 本表（设计定稿）✓
- AC-02 单一 schema：grep "security_report/v1" 字面量仅 security_scanner.py 一处定义
  （run_security_scan 引用导入，契约测试断言）
- AC-03 MCP 契约测试：run_security_scan --json 输出 v1 结构 + server 调用点兼容
- AC-04 SCANNER_SELF_FILES 无已删路径
- AC-05 全量回归 0 failed + compile + release check 6/6
- AC-06 版本 3.12.53
- AC-07 独立审查 GO（hooks/ 零改动）
