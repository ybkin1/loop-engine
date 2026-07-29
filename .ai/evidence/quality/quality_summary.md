# 质量报告 · loop-engine · 2026-07-27 10:49

| 检查项 | 结果 | 门槛 | 状态 |
|--------|------|------|------|
| lint | 765 | 0 | ❌ |
| typecheck | 1 | 0 | ❌ |
| test | 0/0 | 0 | ✅ |
| coverage | 0 | 80 | ❌ |
| audit | {'HIGH': 0, 'CRITICAL': 0, 'MODERATE': 0, 'LOW': 0} | {'HIGH': 0, 'CRITICAL': 0} | ✅ |
| build | 1 | 0 | ❌ |
| compile | 0 | 0 | ✅ |

**结论：BLOCKED**

## 阻断项
- lint: 765 > 0
- typecheck: 1 > 0
- coverage: 0 < 80
- build: exit code != 0