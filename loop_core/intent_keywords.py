"""
Intent Router — 域检测词表与正则常量（T-0110 批 B-1 拆分产物，D5-4 外提）。

从 loop_core/intent_router.py 外提（design-common-weakness.md 1.3 边界：
"关键词常量表（DOMAIN_KEYWORDS 等大表）:35 起"）。纯数据常量表，
零导入、零副作用，供 intent_detection / intent_router 壳共同消费。

内容（原文件逐字迁移，行为零变化）：
- DOMAIN_KEYWORDS / LIGHTWEIGHT_KEYWORDS / HIGH_RISK_KEYWORDS /
  MEDIUM_RISK_KEYWORDS / SCALE_INDICATORS / MAX_COMPLEXITY /
  MIN_COMPLEXITY
- 变更类型词表：BUG_FIX_KEYWORDS / FEATURE_ADD_KEYWORDS /
  REFACTOR_KEYWORDS / REQUIREMENT_CHANGE_KEYWORDS / QUALITY_FIX_KEYWORDS
- 否定语境模式：_NEGATION_PATTERNS

public 面由 intent_router 壳 re-export 保持（from loop_core.
intent_router import * 兼容）。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Domain-detection keyword maps
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "web": [
        "html", "css", "javascript", "typescript", "react", "vue", "angular",
        "svelte", "next.js", "nuxt", "frontend", "front-end", "browser",
        "dom", "responsive", "webpack", "vite", "spa", "ssr", "seo",
        "tailwind", "bootstrap", "web app", "webapp", "website", "web",
    ],
    "mobile": [
        "ios", "android", "react native", "flutter", "swift", "kotlin",
        "mobile", "app store", "google play", "cordova", "capacitor",
        "pwa",
    ],
    "api": [
        "rest", "graphql", "grpc", "api", "endpoint", "openapi", "swagger",
        "http", "websocket", "rpc", "soap", "json api", "webhook",
        "backend",
    ],
    "data": [
        "database", "sql", "nosql", "postgresql", "mysql", "mongodb",
        "sqlite", "redis", "etl", "data pipeline", "analytics", "olap",
        "data warehouse", "migration", "schema", "orm", "query",
        "cassandra", "dynamodb", "bigquery", "snowflake", "databricks",
        "data lake",
    ],
    "cli": [
        "cli", "command line", "terminal", "console", "argparse", "click",
        "typer", "shell", "bash", "scripting", "cron", "batch",
    ],
    "embedded": [
        "iot", "embedded", "firmware", "microcontroller", "arduino",
        "raspberry pi", "esp32", "rtos", "hardware", "sensor",
        "bluetooth low energy", "ble", "mqtt",
    ],
    "cloud_infra": [
        "aws", "azure", "gcp", "terraform", "kubernetes", "docker",
        "ci/cd", "pipeline", "infrastructure", "serverless", "lambda",
        "ec2", "s3", "cloudfront", "iam", "vpc", "helm", "ansible",
    ],
    "ai_ml": [
        "machine learning", "ml", "ai", "deep learning", "neural network",
        "llm", "transformer", "gpt", "bert", "nlp", "computer vision",
        "training", "inference", "fine-tuning", "rag", "embedding",
        "model", "pytorch", "tensorflow", "scikit-learn", "jupyter",
        "data science",
    ],
}

# Low-risk keyword indicators (suggest LIGHTWEIGHT-eligible tasks)
LIGHTWEIGHT_KEYWORDS: list[str] = [
    "simple", "quick", "small", "one-off", "oneoff", "single file",
    "single-file", "bug fix", "bugfix", "minor", "typo", "spelling",
    "comment", "rename", "refactor single", "fix lint", "lint fix",
    "format", "add docstring", "update readme", "readme", "changelog",
    "trivial", "cosmetic", "clean up import", "organize import",
]

# High-risk keywords that trigger automatic escalation
HIGH_RISK_KEYWORDS: list[str] = [
    "payment", "billing", "invoice", "credit card", "subscription",
    "production", "live environment", "prod data",
    "auth", "authentication", "authorization", "permission", "acl", "rbac",
    "password", "secret", "token", "credential", "api key",
    "database migration", "schema migration", "data migration",
    "pii", "gdpr", "hipaa", "compliance", "regulatory",
    "encryption", "cryptography", "ssl", "tls", "certificate",
    "security", "vulnerability", "xss", "csrf", "sql injection",
    "audit", "logging sensitive", "access control",
    "deploy to production", "release to prod",
    "user data", "customer data", "personal data",
]

# Medium-risk keywords (suggest at least STANDARD)
MEDIUM_RISK_KEYWORDS: list[str] = [
    "api", "rest", "graphql", "endpoint", "backend",
    "deploy", "deployment", "ci/cd", "pipeline",
    "integration", "third-party", "external service",
    "module", "package", "library", "plugin",
    "refactor", "rewrite", "restructure",
    "test suite", "unit test", "integration test", "e2e test",
    "performance", "optimize", "cache", "caching",
    "async", "concurrency", "parallel", "threading",
    "microservice", "service",
    "breaking change", "deprecation",
    "multi-module", "monorepo",
]

# Scale indicators (each occurrence increments a complexity counter)
SCALE_INDICATORS: list[tuple[str, float]] = [
    (r"\bmicroservice", 0.05),
    (r"\bmonorepo", 0.05),
    (r"\benterprise", 0.05),
    (r"\bscal(e|able|ing|ability)", 0.04),
    (r"\breal.?time", 0.03),
    (r"\bdistributed", 0.04),
    (r"\bhigh.?availability", 0.05),
    (r"\bfault.?tolerant", 0.04),
    (r"\bmulti.?tenant", 0.04),
    (r"\blegacy", 0.03),
    (r"\bmigration", 0.03),
    (r"\bregression", 0.03),
    (r"\bzero.?downtime", 0.05),
    (r"\bblue.?green", 0.05),
    (r"\bcanary", 0.05),
    (r"\bfeature.?flag", 0.03),
    (r"\bab\s+test", 0.03),
    (r"\bobservability", 0.03),
    (r"\bmonitoring", 0.03),
    (r"\balerting", 0.03),
    (r"\breplication", 0.04),
    (r"\bsharding", 0.04),
    (r"\bpartitioning", 0.03),
    (r"\bmessage.?queue", 0.04),
    (r"\bevent.?driven", 0.04),
    (r"\bstreaming", 0.04),
    (r"\bbatch.?processing", 0.03),
    (r"\bml\b|machine.?learning|ai\b|\bllm\b", 0.05),
    (r"\bcompliance", 0.05),
    (r"\bregulatory", 0.05),
    (r"\bsox\b|\bhipaa\b|\bgdpr\b|\bpci", 0.06),
]

MAX_COMPLEXITY = 1.0
MIN_COMPLEXITY = 0.0


# ---------------------------------------------------------------------------
# Keyword maps for change type detection
# ---------------------------------------------------------------------------

BUG_FIX_KEYWORDS: list[str] = [
    "bug", "fix bug", "修复", "defect", "缺陷", "crash", "崩溃",
    "broken", "坏了", "不工作", "not working", "异常", "exception",
    "报错", "出错",
]

FEATURE_ADD_KEYWORDS: list[str] = [
    "新增", "添加功能", "加一个", "新功能", "new feature", "add feature",
    "implement", "实现", "增加", "支持", "support for",
]

REFACTOR_KEYWORDS: list[str] = [
    "重构", "refactor", "clean up", "整理", "restructure", "重组",
    "simplify", "简化", "优化结构", "拆分", "合并",
]

REQUIREMENT_CHANGE_KEYWORDS: list[str] = [
    "需求变了", "需求变更", "改成", "调整需求", "requirement change",
    "不再需要", "变更范围", "change scope", "修改需求",
]

QUALITY_FIX_KEYWORDS: list[str] = [
    "测试没过", "覆盖率", "lint", "type check", "类型检查",
    "性能问题", "performance issue", "加测试", "补测试", "安全漏洞",
    "security fix", "补文档", "测试", "单元测试", "集成测试",
]


# Negation patterns — if these appear near a keyword, don't set the flag
_NEGATION_PATTERNS: list[str] = [
    r'\b(?:remove|delete|drop|eliminate|get rid of|ditch)\s+(?:the\s+)?',
    r"\b(?:don't|do not|won't|will not)\s+(?:need|use|have|want)\s+(?:a\s+)?(?:the\s+)?",
    r'\b(?:without|no)\s+(?:a\s+)?(?:the\s+)?(?:any\s+)?',
    r'\bnot\s+(?:using|needing|having)\s+(?:a\s+)?(?:the\s+)?',
]
