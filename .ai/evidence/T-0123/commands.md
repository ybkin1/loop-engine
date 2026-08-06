# T-0123 commands

## 执行命令记录

```bash
# 1. ROLE_CHALLENGES 补 test-engineer（loop_core/role_capability.py）
#    CHALLENGE-TE-001（pytest/SD-020 边界 off-by-one/SD-021 异常未处理/3 pass_conditions）

# 2. certification_runner 共享常量（scripts/certification_runner.py）
#    + sys.path 注入 + SECURITY_REPORT_V1_SCHEMA 引用（L613 字面量替换）

# 3. deep_probe challenges 检查补全（tests/deep_probe_v35.py，12/12）

# 4. 测试
C:/Python312/python.exe -m pytest tests/test_t0123_challenge_completion.py -q   # 8 passed
C:/Python312/python.exe tests/deep_probe_v35.py                                # 266+ passed 0 failed

# 5. KNOWN_ISSUES：ROLE_CHALLENGES-gap / certification_runner 两条关闭

# 6. 全量回归 + compile + bump
C:/Python312/python.exe -m pytest tests/ -q
C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0123/compile-evidence.json
C:/Python312/python.exe scripts/release.py bump --to 3.12.58 --title "T-0123: ROLE_CHALLENGES 补全 + certification_runner 字面量统一"
```

## 遗留观察

- `test_manifest_t0095`：active 在途态，closeout 自愈。
- `test_release version_sync`：HEAD 3.12.57 vs 载体 3.12.58，提交后自愈（F-03）。

## 审查观察登记（GO，非阻塞）

- `agents/security-engineer/SKILL.md:39` 文档示例含 security_report/v1 字面量
  （pre-existing 文档，非定义点）→ 留待后续文档清扫（不在本任务范围）。
