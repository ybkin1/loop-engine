# 安全扫描报告 · loop-engine · 2026-08-02 10:43

| 扫描项 | 结果 | 详情 |
|--------|------|------|
| dependency_scan | ❌ | H:1 C:0 M:0 L:0 (pip-audit) |
| secret_scan | ❌ | 7 个疑似密钥 |
| injection_scan | ❌ | HIGH:26 MEDIUM:4 |
| permission_audit | ✅ | 0 个高危未鉴权路由（共 5 个） |

**结论：BLOCKED**

## 阻断项

### dependency_scan
- HIGH: 1, CRITICAL: 0

### secret_scan
- `scripts\certification_runner.py:686` — Generic Password Assignment (plaintext)
- `tests\test_guard_health.py:32` — Generic Password Assignment (plaintext)
- `tests\test_hook_guards.py:24` — Generic Password Assignment (plaintext)
- `tests\test_hook_guards.py:44` — Generic Secret Assignment
- `tests\test_verdicts.py:215` — Generic Secret Assignment
- `tests\seeded_defects\test_project\src\user_service.py:12` — OpenAI API Key
- `agents\references\role-capability-profiles.md:757` — Generic Password Assignment (plaintext)

### injection_scan
- `scripts\security_scan.py:42` — os.system(): (r'os\.system\s*\(', "P1", "Unsafe os.system() call"),
- `scripts\security_scan.py:46` — eval(): (r'eval\s*\(', "P0", "Dangerous eval() call"),
- `scripts\security_scan.py:47` — exec(): (r'exec\s*\(', "P0", "Dangerous exec() call"),
- `tests\test_code_quality.py:97` — os.system(): assert any(p.search('os.system("echo test")') for p, _, _, _ in _OS_COMMAND_PATT
- `tests\test_content_guard_semantic.py:194` — eval(): "content": 'code = eval("x + {val}")\n',