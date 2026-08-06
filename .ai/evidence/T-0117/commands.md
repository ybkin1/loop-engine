# T-0117 commands

## 执行命令记录

```bash
# 1. 现状确认（T-0109 遗留 #3 双实现）
grep -n "security_report/v1" agents/security-engineer/scripts/run_security_scan.py  # generate_report 内联 schema
#    loop_core/security_scanner.py 无 CLI/无 schema

# 2. 设计定稿
#    .ai/evidence/T-0117/design/contract-unification.md（四维差异表 + 收敛决策）

# 3. loop_core 收敛实现（add-only）
#    loop_core/security_scanner.py：
#    + SECURITY_REPORT_V1_SCHEMA / SECURITY_REPORT_V1_FIELDS
#    + build_v1_report / validate_v1_report / cli_exit_code
#    + SecurityReport.to_v1_report()（to_dict 保持）
#    + main() CLI（--project-root/--output-dir/--json，退出码 0/2）

# 4. run_security_scan.py 收敛
#    + _PROJECT_ROOT sys.path 注入 + import build_v1_report/validate_v1_report
#    + generate_report 改引 build_v1_report（输出逐字段等价）
#    + SCANNER_SELF_FILES 清 2 条已删路径（T-0113 P3-5）
#    + stdout 泄漏修复：PASS 消息 file=sys.stderr（既有 bug：--json 契约被破坏）

# 5. 测试
C:/Python312/python.exe -m pytest tests/test_t0117_contract_unification.py -q   # 13 passed
C:/Python312/python.exe -m pytest tests/test_security_scan_whitelist.py -q      # 18 passed（fixture 改现存白名单文件）
C:/Python312/python.exe -m pytest tests/test_t0108_fixes.py -q                  # 34 passed（repair 后）

# 6. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0117/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.53 --title "T-0117: 安全扫描双实现收敛（security_report/v1 契约统一）"
```

## 环境适配说明

- 本机 `C:\Python312\python312._pth` 使 python 子进程处于隔离模式
  （`sys.flags.isolated=1` + `safe_path=True`）：忽略 cwd 与 PYTHONPATH。
  → 子进程 CLI 测试用 `-c` bootstrap 显式 `sys.path.insert(0, PROJECT)`。
- 扫描器排除逻辑按绝对路径子串匹配（`test_` 等关键字）→ pytest tmp 目录
  名含 test_ 会被排除，测试用 `tempfile.mkdtemp()`。

## 既有 bug 修复（顺带发现）

`run_security_scan.py` 的 PASS 消息原输出到 stdout，`--json` 模式下 stdout =
JSON + 额外行 → `tools/server.py::_run_security_scan` 的 `json.loads(r.stdout)`
在 PASS 场景抛 JSONDecodeError（MCP security_scan_run 返回 error）。
已改 stderr，契约测试 `test_run_security_scan_json_is_v1` 锁定。

## 遗留观察

- `test_manifest_t0095`：active 在途态（HANDOFF 引用 T-0117 manifest 未生成），
  closeout 自愈。
- `test_release version_sync`：HEAD 3.12.52 vs 载体 3.12.53，提交后自愈（F-03）。

## 审查观察登记（GO，P3 不阻断）

1. run_security_scan.py 中 SECURITY_REPORT_V1_SCHEMA unused import → 已删除。
2. CHANGELOG v3.12.53 条目为 bump 工具通用模板（记录质量建议，不阻断）。
3. `scripts/certification_runner.py:613` 既有 security_report/v1 字面量（pre-existing，
   非 T-0117 引入）→ KNOWN_ISSUES 登记。
4. bump 后 continuity 漂移（version-manifest.yaml）→ closeout 执行
   `validate_state --repair` + HANDOFF 重生成，提交后全量应 0 failed。
