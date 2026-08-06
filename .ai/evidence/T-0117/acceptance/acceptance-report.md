# T-0117 验收报告

## 验收结论：PASS（7/7 AC）

| AC | 验收项 | 证据 | 结果 |
|----|--------|------|------|
| AC-01 | 契约差异表 | design/contract-unification.md（schema/退出码/判定/CLI 四维收敛前后对照） | ✅ |
| AC-02 | 单一 schema 实现 | grep：security_report/v1 字面量仅 loop_core/security_scanner.py:329 定义；run_security_scan.py 改引 import；契约测试 test_single_schema_definition 锁定 | ✅ |
| AC-03 | MCP security_scan_run 契约测试 | test_run_security_scan_json_is_v1（--json 输出 v1 校验）+ 13/13 契约测试；server.py 零改动 | ✅ |
| AC-04 | 无已删路径残留 | SCANNER_SELF_FILES AST 断言无 12 个已删路径；test_scanner_self_files_no_deleted_paths | ✅ |
| AC-05 | 全量回归 + compile + release check | 4186 passed / 1 failed（仅 manifest 在途态）；compile 87/87；release check 提交后复验 6/6 | ✅ |
| AC-06 | 版本 3.12.53 | 8 载体 3.12.53 + CHANGELOG T-0117 条目；提交后 version_sync 自愈（F-03） | ✅ |
| AC-07 | 独立审查 GO | **GO**（4 项 P3 观察全部处理：unused import 删除/CHANGELOG 记录/certification_runner 登记/漂移 repair） | ✅ |

## 关键事实

- 收敛：schema 单一数据源 → loop_core/security_scanner.py（build_v1_report/validate_v1_report/
  cli_exit_code/CLI main）；run_security_scan.py 改引共享构建器（输出逐字段等价）
- **顺带修复既有 bug**：run_security_scan.py PASS 消息 stdout 泄漏 → server MCP
  security_scan_run 在 PASS 场景 JSONDecodeError（契约测试锁定）
- SCANNER_SELF_FILES 清 2 条已删路径（T-0113 P3-5 闭环）
- hooks/ 零改动；tools/server.py 零改动；SecurityReport.to_dict 等既有 API 零改动（add-only）
- 版本 3.12.53

## 提交说明

- 提交 subject：`v3.12.53: T-0117 — 安全扫描双实现收敛（security_report/v1 契约统一 + MCP 兼容 + SCANNER_SELF_FILES 清理）`
- 提交后复验：version_sync、manifest 引用、release check 6/6、全量 0 failed
