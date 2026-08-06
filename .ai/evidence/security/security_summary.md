# 安全扫描报告 · loop-engine · 2026-08-06 19:01

| 扫描项 | 结果 | 详情 |
|--------|------|------|
| dependency_scan | ⏭️ | SKIPPED — pip-audit 环境不可用（exit=1）:   File "C:\Python312\Lib\site-packages\pip_audit\_virtual_env.py", line 9, in <module>;     import venv; ModuleNotFoundError: No module named 'venv' |
| secret_scan | ✅ | 0 个疑似密钥 |
| injection_scan | ✅ | HIGH:0 MEDIUM:0 |
| permission_audit | ✅ | 0 个高危未鉴权路由（共 5 个） |

**结论：PASS**

全部安全扫描通过。