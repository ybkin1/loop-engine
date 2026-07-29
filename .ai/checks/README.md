# Loop 语义检查规则库

T-0078 P0: Domain-Specific Code Logic Checks.

框架特定规则文件按 `<framework>.rules.yaml` 命名。
content_guard.py 在 PreToolUse 时加载匹配 glob 的规则文件并检查写入内容。

## 已注册规则

| 文件 | 框架 | 规则数 |
|------|------|--------|
| nextjs.rules.yaml | Next.js | 7 |
