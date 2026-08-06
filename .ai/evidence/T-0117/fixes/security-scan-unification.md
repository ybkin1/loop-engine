# T-0117 修复记录：security-scan-unification

## 背景

T-0109 遗留 #3：`loop_core/security_scanner.py`（进程内库）与
`agents/security-engineer/scripts/run_security_scan.py`（CLI 编排）双实现并存，
各自生成报告结构。收敛决策：以 run_security_scan.py 既有的 security_report/v1
顶层结构为输出契约标准，schema 常量 + 构建器 + 校验器收敛到 loop_core
（单一数据源），MCP security_scan_run 输出契约兼容为硬约束。

## 修改清单

| 文件 | 修改 |
|------|------|
| `loop_core/security_scanner.py` | +`SECURITY_REPORT_V1_SCHEMA`/`SECURITY_REPORT_V1_FIELDS`/`build_v1_report`/`validate_v1_report`/`cli_exit_code`/`main`（CLI：--project-root/--output-dir/--json，退出码 0/2）+ `SecurityReport.to_v1_report()`（add-only，`to_dict()` 保持不变） |
| `agents/security-engineer/scripts/run_security_scan.py` | +项目根 sys.path 注入（独立脚本可 import loop_core）+ `generate_report` 改引 `build_v1_report`（输出逐字段等价）+ `SCANNER_SELF_FILES` 清除 2 条已删路径（T-0113 P3-5）+ **stdout 泄漏修复**（PASS 消息改 stderr——既有 bug：--json 模式下 stdout 混入额外行，server MCP 在 PASS 时 JSONDecodeError） |
| `tests/test_t0117_contract_unification.py` | 新增 13 项契约测试（单一 schema 断言/v1 校验/判定映射/CLI 退出码/MCP 兼容/SCANNER_SELF_FILES 无残留/库 API 不受影响） |
| `tests/test_security_scan_whitelist.py` | fixture 改用现存白名单文件（run_security_scan.py）替代已删的 scripts/security_scan.py（保持"扫描器自身豁免"语义） |
| `tools/server.py` | 零改动（子进程契约兼容验证） |

## 关键设计决策

1. **add-only 兼容**：`SecurityReport.to_dict()` 与 `scan_security()`/`SecurityScanner.scan()`
   保持原样（既有消费方：run_quality_gates/loop_self_audit/既有测试零破坏）。
2. **判定语义统一**：loop_core CLI critical/high → exit 2（BLOCKED，fail-closed），
   与 run_security_scan 任一 scan blocked → exit 2 同级。
3. **stdout 泄漏修复**（既有 bug）：`print("[run_security_scan] PASS ...")` 原打到
   stdout，--json 模式输出 JSON + 额外行 → `server._run_security_scan` 的
   `json.loads(r.stdout)` 在 PASS 场景会抛 JSONDecodeError（MCP security_scan_run
   返回 error）。改为 stderr，恢复 --json 纯净契约。
4. **测试环境适配**：本机 python312._pth 隔离模式（sys.flags.isolated=1，忽略
   cwd/PYTHONPATH）→ 子进程 CLI 测试用 `-c` bootstrap 显式插入项目根；
   扫描器排除逻辑按绝对路径子串匹配 → 测试用 tempfile.mkdtemp 避免 pytest
   tmp 目录名含 test_ 被排除。

## 验证

- 契约测试 13/13 PASS；whitelist 18/18 PASS；t0108 34 PASS；validate EXIT=0
- 全量回归结果见 commands.md（预期仅 manifest 在途态 + version_sync 提交前 2 项自愈类）
