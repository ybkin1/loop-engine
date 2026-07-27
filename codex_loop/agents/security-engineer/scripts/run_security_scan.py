"""
run_security_scan.py — 安全扫描编排脚本（安全工程师使用）。

确定性代码，不依赖 LLM。依次执行四类安全扫描：
  1. 依赖 CVE 扫描 — 优先复用质量工程师审计结果，否则独立运行
  2. 密钥泄露扫描 — 内置正则匹配常见密钥模式
  3. 注入面检测   — 扫描高危代码模式（eval/os.system/SQL 拼接等）
  4. 权限模型审计 — 检查路由文件鉴权中间件

输出文件（写入 --output-dir 或 .ai/evidence/security/）：
    security_report.json   — 机器可读
    security_summary.md    — 人可读

退出码：0 = PASS（无 BLOCKED 项）；2 = 有 BLOCKED 项。

用法：
    python run_security_scan.py --project-root <dir> [--output-dir <dir>] [--json]
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.dont_write_bytecode = True

EXIT_PASS = 0
EXIT_BLOCK = 2

# ──────────────────────────────────────────────
# 0. 工具函数
# ──────────────────────────────────────────────

def _read_file(path: Path) -> Optional[str]:
    """安全读取文件内容。"""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _find_files(project_root: Path, extensions: Tuple[str, ...],
                exclude_dirs: Optional[Set[str]] = None) -> List[Path]:
    """递归查找指定扩展名的文件，排除特定目录。"""
    if exclude_dirs is None:
        exclude_dirs = {".git", "node_modules", ".venv", "venv", ".tox",
                        "__pycache__", "build", "dist", ".eggs", ".ai",
                        ".next", ".nuxt", ".cache", "coverage"}
    files = []
    for ext in extensions:
        for fp in project_root.rglob(f"*{ext}"):
            if any(part in exclude_dirs for part in fp.parts):
                continue
            files.append(fp)
    return files


# ──────────────────────────────────────────────
# 1. 依赖 CVE 扫描
# ──────────────────────────────────────────────

def _reuse_quality_audit(project_root: Path) -> Optional[Dict[str, Any]]:
    """尝试复用质量工程师的审计结果（1 小时内有效）。"""
    audit_path = project_root / ".ai" / "evidence" / "quality" / "quality_report.json"
    if not audit_path.is_file():
        return None
    try:
        report = json.loads(audit_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None

    # 检查时间戳
    ts_str = report.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_str)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > 3600:  # 超过 1 小时
            return None
    except (ValueError, TypeError):
        return None

    # 查找 audit 项
    for check in report.get("checks", []):
        if check.get("name") == "audit":
            return check
    return None


def _run_npm_audit(project_root: Path) -> Tuple[Dict[str, int], str]:
    """运行 npm audit 并解析结果。"""
    counts = {"HIGH": 0, "CRITICAL": 0, "MODERATE": 0, "LOW": 0}
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            return counts, ""

        # npm audit 在检测到漏洞时退出码非零，但仍输出 JSON
        raw = result.stdout.strip()
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
                vulns = data.get("vulnerabilities", {}) if isinstance(data, dict) else {}
                for v in (vulns.values() if isinstance(vulns, dict) else []):
                    if isinstance(v, dict):
                        sev = v.get("severity", "").upper()
                        if sev in counts:
                            counts[sev] += 1
                return counts, raw[:500]
            except json.JSONDecodeError:
                pass
        return {"HIGH": 1, "CRITICAL": 0, "MODERATE": 0, "LOW": 0}, raw[:500]
    except FileNotFoundError:
        return counts, "npm 不可用"
    except subprocess.TimeoutExpired:
        return counts, "npm audit 超时"
    except Exception as e:
        return counts, str(e)


def _run_pip_audit(project_root: Path) -> Tuple[Dict[str, int], str]:
    """运行 pip-audit 并解析结果。"""
    counts = {"HIGH": 0, "CRITICAL": 0, "MODERATE": 0, "LOW": 0}
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        return counts, "未找到 requirements.txt"
    try:
        result = subprocess.run(
            ["pip-audit", "-r", "requirements.txt", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )
        raw = result.stdout.strip()
        if raw.startswith("["):
            try:
                items = json.loads(raw)
                for item in items:
                    if isinstance(item, dict):
                        vulns = item.get("vulns", [])
                        if isinstance(vulns, list):
                            for v in vulns:
                                if isinstance(v, dict):
                                    sev = (v.get("severity") or "").upper()
                                    if sev in counts:
                                        counts[sev] += 1
                return counts, raw[:500]
            except json.JSONDecodeError:
                pass
        if result.returncode != 0:
            counts["HIGH"] = max(1, counts["HIGH"])
        return counts, raw[:500]
    except FileNotFoundError:
        return counts, "pip-audit 不可用"
    except subprocess.TimeoutExpired:
        return counts, "pip-audit 超时"
    except Exception as e:
        return counts, str(e)


def _detect_project_type(project_root: Path) -> str:
    """检测项目类型：python / javascript / unknown。"""
    if (project_root / "package.json").exists():
        return "javascript"
    if (project_root / "pyproject.toml").exists() or (project_root / "requirements.txt").exists():
        return "python"
    return "unknown"


def run_dependency_scan(project_root: Path) -> Dict[str, Any]:
    """
    依赖 CVE 扫描。优先复用质量工程师的结果（1 小时内）。
    若不可用则独立运行 npm audit 或 pip-audit。
    """
    # 尝试复用
    reused = _reuse_quality_audit(project_root)
    if reused is not None:
        value = reused.get("value", {})
        if isinstance(value, dict):
            counts = {k.upper(): v for k, v in value.items()}
        else:
            counts = {"HIGH": 0, "CRITICAL": 0, "MODERATE": 0, "LOW": 0}
        return {
            "name": "dependency_scan",
            "status": "pass" if reused.get("status") == "pass" else "blocked",
            "counts": counts,
            "source": "quality-engineer (reused)",
            "skipped": False,
        }

    # 独立扫描
    pt = _detect_project_type(project_root)
    if pt == "javascript":
        counts, raw = _run_npm_audit(project_root)
    elif pt == "python":
        counts, raw = _run_pip_audit(project_root)
    else:
        return {
            "name": "dependency_scan",
            "status": "pass",
            "counts": {"HIGH": 0, "CRITICAL": 0, "MODERATE": 0, "LOW": 0},
            "source": "unknown project type, skipped",
            "skipped": True,
        }

    blocked = counts.get("HIGH", 0) > 0 or counts.get("CRITICAL", 0) > 0
    return {
        "name": "dependency_scan",
        "status": "blocked" if blocked else "pass",
        "counts": counts,
        "source": "npm audit" if pt == "javascript" else "pip-audit",
        "raw": raw[:500] if raw else "",
        "skipped": False,
    }


# ──────────────────────────────────────────────
# 2. 密钥泄露扫描（内置正则）
# ──────────────────────────────────────────────

# 密钥正则模式
SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    # (名称, 正则, 说明)
    ("AWS Access Key", r"AKIA[0-9A-Z]{16}", "AWS Access Key ID (AKIA...)"),
    ("GitHub Token", r"gh[pousr]_[A-Za-z0-9_]{36,255}", "GitHub Personal Access Token"),
    ("OpenAI API Key", r"sk-[A-Za-z0-9]{32,96}", "OpenAI API Key"),
    ("Private Key Block", r"-----BEGIN\s*(?:RSA|EC|DSA|OPENSSH|PGP)?\s*PRIVATE\s+KEY\s*-----",
     "PEM Private Key block"),
    ("Generic Password Assignment (plaintext)", r'(?:password|passwd|pwd|secret)\s*[=:]\s*["\'][^"\']+["\']',
     "Plaintext password in code"),
    ("Generic Secret Assignment", r'(?:api_key|apikey|api_secret|secret_key|auth_token)\s*[=:]\s*["\'][^"\']+["\']',
     "API secret in code"),
    ("Basic Auth URL", r"https?://[^@]+:[^@]+@\S+", "URL with embedded credentials"),
    ("Slack Bot Token", r"xox[baprs]-[0-9a-zA-Z\-]{10,}", "Slack Bot Token"),
    ("JWT Token (hardcoded)", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
     "Hardcoded JWT token"),
    ("Generic token assignment", r'(?:token)\s*[=:]\s*["\'][A-Za-z0-9_\-\.]{20,}["\']',
     "Generic token in code"),
    ("Connection string with password", r'(?:mongodb|postgresql|mysql|redis)://[^:]+:[^@]+@',
     "Database connection string with password"),
]

# 排除模式（通常不是真正的密钥）
EXCLUDE_PATTERNS: List[re.Pattern] = [
    re.compile(r"example", re.IGNORECASE),
    re.compile(r"placeholder", re.IGNORECASE),
    re.compile(r"your[-_]?(key|token|secret)", re.IGNORECASE),
    re.compile(r"TODO", re.IGNORECASE),
    re.compile(r"xxxx"),
    re.compile(r"<\w+>"),
    re.compile(r"\$\{?\w+\}?"),
    re.compile(r"process\.env", re.IGNORECASE),
    re.compile(r"os\.environ", re.IGNORECASE),
    re.compile(r"ENV\[", re.IGNORECASE),
]


def _is_excluded(line: str, match_text: str) -> bool:
    """检查匹配文本是否被排除模式匹配。"""
    for pat in EXCLUDE_PATTERNS:
        if pat.search(line):
            return True
    # 公共示例密钥
    if "sk-" in match_text and len(match_text) < 40:
        return True
    if match_text.count("0") + match_text.count("x") + match_text.count("X") > len(match_text) * 0.4:
        return True
    return False


def run_secret_scan(project_root: Path) -> Dict[str, Any]:
    """内置正则扫描密钥泄露。"""
    findings: List[Dict[str, Any]] = []
    # 搜索常见代码文件
    exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml",
            ".toml", ".env", ".cfg", ".ini", ".sh", ".bash", ".zsh",
            ".txt", ".md", ".java", ".go", ".rs", ".rb", ".php")
    files = _find_files(project_root, exts)

    for fp in files:
        content = _read_file(fp)
        if not content:
            continue
        try:
            rel = fp.relative_to(project_root)
        except ValueError:
            rel = fp

        for line_no, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            for pattern_name, pattern_re, description in SECRET_PATTERNS:
                for m in re.finditer(pattern_re, line):
                    matched = m.group(0)
                    if _is_excluded(line, matched):
                        continue
                    findings.append({
                        "file": str(rel),
                        "line": line_no,
                        "rule": pattern_name,
                        "match": matched[:80] + ("..." if len(matched) > 80 else ""),
                        "description": description,
                    })

    blocked = len(findings) > 0
    return {
        "name": "secret_scan",
        "status": "blocked" if blocked else "pass",
        "findings": findings,
        "files_scanned": len(files),
        "skipped": False,
    }


# ──────────────────────────────────────────────
# 3. 注入面检测
# ──────────────────────────────────────────────

# HIGH 风险模式（命中即 BLOCKED）
HIGH_RISK_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("os.system()", re.compile(r"os\.system\s*\("), "shell 命令注入面"),
    ("subprocess shell=True", re.compile(r"subprocess\..*?shell\s*=\s*True"), "shell 注入面"),
    ("eval()", re.compile(r"\beval\s*\("), "eval 代码注入"),
    ("exec()", re.compile(r"\bexec\s*\("), "exec 代码注入"),
    ("SQL concatenation (f-string)", re.compile(r"f[\"'].*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b.*[\"']",
                                                  re.IGNORECASE), "SQL 注入面 (f-string)"),
    ("SQL concatenation (+) ", re.compile(r"[\"'].*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b.*[\"']\s*\+",
                                             re.IGNORECASE), "SQL 注入面 (字符串拼接)"),
    ("SQL format (%)", re.compile(r"[\"'].*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b.*[\"']\s*%\s*\(",
                                     re.IGNORECASE), "SQL 注入面 (格式字符串)"),
    ("dangerouslySetInnerHTML", re.compile(r"dangerouslySetInnerHTML"), "React XSS 注入"),
    ("raw SQL execute", re.compile(r"\.execute\s*\(\s*f?[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b",
                                      re.IGNORECASE), "原始 SQL 执行"),
    ("os.popen()", re.compile(r"os\.popen\s*\("), "进程注入面"),
    ("pickle.loads()", re.compile(r"pickle\.loads?\s*\("), "反序列化注入"),
    ("yaml.load() unsafe", re.compile(r"yaml\.load\s*\([^L]"), "YAML 反序列化注入 (非 safe_load)"),
    ("render_template_string", re.compile(r"render_template_string\s*\("), "服务端模板注入 (SSTI)"),
]

# MEDIUM 风险模式（命中为警告）
MEDIUM_RISK_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("innerHTML assignment", re.compile(r"\.innerHTML\s*="), "DOM XSS (innerHTML)"),
    ("document.write()", re.compile(r"document\.write\s*\("), "DOM XSS (document.write)"),
    ("raw HTML filter", re.compile(r"\|\s*raw\b"), "模板 raw 过滤器"),
    ("bypass sanitization", re.compile(r"bypassSecurityTrust\w+\s*\("), "Angular 安全绕过"),
    ("unsafe HTML binding", re.compile(r"innerHTML|outerHTML|insertAdjacentHTML"), "不安全 HTML 绑定"),
    ("unvalidated redirect", re.compile(r"redirect\s*\(\s*(?:request\.|req\.)", re.IGNORECASE), "未验证跳转"),
    ("command injection via f-string", re.compile(r"os\.(?:system|popen)\s*\(\s*f[\"']"), "命令注入"),
]


def run_injection_scan(project_root: Path) -> Dict[str, Any]:
    """扫描代码中的注入面。"""
    exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".jinja2",
            ".jinja", ".hbs", ".ejs", ".php", ".rb")
    files = _find_files(project_root, exts)

    high_findings: List[Dict[str, Any]] = []
    medium_findings: List[Dict[str, Any]] = []

    for fp in files:
        content = _read_file(fp)
        if not content:
            continue
        try:
            rel = fp.relative_to(project_root)
        except ValueError:
            rel = fp

        for line_no, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # 跳过注释行（降低误报）
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if stripped.startswith("*") or stripped.startswith("*"):
                continue  # 块注释内部

            # HIGH 风险
            for rule_name, pattern, description in HIGH_RISK_PATTERNS:
                if pattern.search(line):
                    high_findings.append({
                        "file": str(rel),
                        "line": line_no,
                        "rule": rule_name,
                        "severity": "HIGH",
                        "description": description,
                        "snippet": stripped[:120],
                    })

            # MEDIUM 风险
            for rule_name, pattern, description in MEDIUM_RISK_PATTERNS:
                if pattern.search(line):
                    medium_findings.append({
                        "file": str(rel),
                        "line": line_no,
                        "rule": rule_name,
                        "severity": "MEDIUM",
                        "description": description,
                        "snippet": stripped[:120],
                    })

    blocked = len(high_findings) > 0
    return {
        "name": "injection_scan",
        "status": "blocked" if blocked else "pass",
        "high_findings": high_findings,
        "medium_findings": medium_findings,
        "files_scanned": len(files),
        "skipped": False,
    }


# ──────────────────────────────────────────────
# 4. 权限模型审计
# ──────────────────────────────────────────────

# 鉴权中间件模式（存在表示路由受保护）
AUTH_MIDDLEWARE_PATTERNS = [
    # Python
    re.compile(r"@login_required"),
    re.compile(r"@permission_required"),
    re.compile(r"@jwt_required"),
    re.compile(r"Depends\s*\(\s*get_current_user\b"),
    re.compile(r"require_auth"),
    # JavaScript / Express
    re.compile(r"authMiddleware\b"),
    re.compile(r"requireAuth\b"),
    re.compile(r"isAuthenticated\b"),
    re.compile(r"authenticate\s*\("),
    # Next.js
    re.compile(r"getServerSession\b"),
    # Generic
    re.compile(r"@Authorize\b"),
    re.compile(r"@Roles\b"),
    re.compile(r"hasPermission\b"),
]

# 路由定义模式（表明这是一个需要鉴权的端点）
ROUTE_PATTERNS = [
    # Python Flask/FastAPI
    re.compile(r"@(?:app|router|bp)\.(?:route|get|post|put|patch|delete)\s*\("),
    re.compile(r"@(?:app|router|bp)\.(?:api_route)\s*\("),
    # Python Django
    re.compile(r"path\s*\(\s*['\"]"),
    # JavaScript Express
    re.compile(r"(?:app|router)\.(?:get|post|put|patch|delete|use)\s*\("),
    # Next.js API routes
    re.compile(r"export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|PATCH|DELETE)\b"),
]

# 公开路由标记
PUBLIC_ROUTE_PATTERNS = [
    re.compile(r"public\s*=\s*True"),
    re.compile(r"is_public\s*=\s*True"),
    re.compile(r"allow_anonymous"),
    re.compile(r"@public"),
    re.compile(r"skip_auth"),
    re.compile(r"no_auth"),
]


def run_permission_audit(project_root: Path) -> Dict[str, Any]:
    """检查路由文件中每个 POST/PUT/DELETE 端点是否有鉴权中间件。"""
    # 查找可能的路由文件
    route_indicators = ["route", "router", "urls", "api", "endpoint", "controller", "views"]
    exts = (".py", ".ts", ".js", ".tsx", ".jsx")

    all_files = _find_files(project_root, exts)
    route_files = []
    for fp in all_files:
        name_lower = fp.name.lower()
        if any(ind in name_lower for ind in route_indicators):
            route_files.append(fp)
        else:
            # 也检查文件内容是否包含路由定义
            content = _read_file(fp)
            if content:
                for pat in ROUTE_PATTERNS:
                    if pat.search(content):
                        route_files.append(fp)
                        break

    # 去重
    route_files = list(dict.fromkeys(route_files))

    findings: List[Dict[str, Any]] = []

    for fp in route_files:
        content = _read_file(fp)
        if not content:
            continue
        try:
            rel = fp.relative_to(project_root)
        except ValueError:
            rel = fp

        # 检查文件中是否定义了路由
        has_routes = any(pat.search(content) for pat in ROUTE_PATTERNS)
        if not has_routes:
            continue

        # 检查文件是否有全局鉴权中间件
        has_file_level_auth = any(pat.search(content) for pat in AUTH_MIDDLEWARE_PATTERNS)

        # 逐行分析路由和鉴权的关系
        lines = content.splitlines()
        for line_no, line in enumerate(lines, 1):
            # 检查是否是路由定义
            is_route = any(pat.search(line) for pat in ROUTE_PATTERNS)
            if not is_route:
                continue

            # 检查该路由是否为公开路由
            is_public = any(pat.search(line) for pat in PUBLIC_ROUTE_PATTERNS)

            # 检查周围 5 行是否有鉴权中间件
            context_start = max(0, line_no - 5)
            context_end = min(len(lines), line_no + 2)
            context = "\n".join(lines[context_start:context_end])

            has_auth = has_file_level_auth or any(
                pat.search(context) for pat in AUTH_MIDDLEWARE_PATTERNS
            )

            if not has_auth and not is_public:
                # 确定 HTTP 方法
                method = "GET"  # 默认
                if re.search(r"(post|put|patch|delete|POST|PUT|PATCH|DELETE)", line):
                    method_match = re.search(r"(post|put|patch|delete|POST|PUT|PATCH|DELETE)", line)
                    if method_match:
                        method = method_match.group(1).upper()

                findings.append({
                    "file": str(rel),
                    "line": line_no,
                    "method": method,
                    "route": line.strip()[:100],
                    "issue": "路由未挂载鉴权中间件",
                    "severity": "HIGH" if method in ("POST", "PUT", "PATCH", "DELETE") else "MEDIUM",
                })

    # 只阻断高危（写操作无鉴权）
    high_findings = [f for f in findings if f.get("severity") == "HIGH"]
    blocked = len(high_findings) > 0

    return {
        "name": "permission_audit",
        "status": "blocked" if blocked else "pass",
        "findings": findings,
        "high_count": len(high_findings),
        "files_scanned": len(route_files),
        "skipped": False,
    }


# ──────────────────────────────────────────────
# 5. 报告生成
# ──────────────────────────────────────────────

def generate_report(scans: List[Dict[str, Any]], project_root: Path, output_dir: Path) -> str:
    """生成 JSON 报告和 Markdown 摘要。返回 overall 判定。"""
    blocked_by = []
    for scan in scans:
        if scan.get("status") == "blocked":
            blocked_by.append(scan["name"])

    overall = "PASS" if not blocked_by else "BLOCKED"

    # JSON report
    report = {
        "schema": "security_report/v1",
        "role": "security-engineer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": str(project_root.resolve()),
        "scans": scans,
        "overall": overall,
        "blocked_by": blocked_by,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "security_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md_lines = [
        f"# 安全扫描报告 · {project_root.name} · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| 扫描项 | 结果 | 详情 |",
        "|--------|------|------|",
    ]

    for scan in scans:
        status_icon = "✅" if scan["status"] == "pass" else "❌"
        details = ""
        if scan["name"] == "dependency_scan":
            c = scan.get("counts", {})
            details = f"H:{c.get('HIGH',0)} C:{c.get('CRITICAL',0)} M:{c.get('MODERATE',0)} L:{c.get('LOW',0)}"
            if scan.get("source"):
                details += f" ({scan['source']})"
        elif scan["name"] == "secret_scan":
            n = len(scan.get("findings", []))
            details = f"{n} 个疑似密钥"
        elif scan["name"] == "injection_scan":
            hi = len(scan.get("high_findings", []))
            med = len(scan.get("medium_findings", []))
            details = f"HIGH:{hi} MEDIUM:{med}"
        elif scan["name"] == "permission_audit":
            n = scan.get("high_count", 0)
            total = len(scan.get("findings", []))
            details = f"{n} 个高危未鉴权路由（共 {total} 个）"
        if scan.get("skipped"):
            details = "跳过"
        md_lines.append(f"| {scan['name']} | {status_icon} | {details} |")

    md_lines.append("")
    md_lines.append(f"**结论：{overall}**")

    if blocked_by:
        md_lines.append("")
        md_lines.append("## 阻断项")
        for scan in scans:
            if scan["status"] == "blocked":
                md_lines.append("")
                md_lines.append(f"### {scan['name']}")
                if scan["name"] == "dependency_scan":
                    c = scan.get("counts", {})
                    md_lines.append(f"- HIGH: {c.get('HIGH', 0)}, CRITICAL: {c.get('CRITICAL', 0)}")
                elif scan["name"] == "secret_scan":
                    for f in scan.get("findings", []):
                        md_lines.append(f"- `{f['file']}:{f['line']}` — {f['rule']}")
                        if len(md_lines) > 30:
                            md_lines.append(f"- ... 其余 {len(scan['findings']) - len([x for x in scan.get('findings', [])])} 项已折叠")
                            break
                elif scan["name"] == "injection_scan":
                    for f in scan.get("high_findings", []):
                        md_lines.append(f"- `{f['file']}:{f['line']}` — {f['rule']}: {f['snippet'][:80]}")
                        if len(md_lines) > 30:
                            break
                elif scan["name"] == "permission_audit":
                    for f in scan.get("findings", []):
                        if f.get("severity") == "HIGH":
                            md_lines.append(f"- `{f['file']}:{f['line']}` — {f['method']} {f['issue']}")
    else:
        md_lines.append("")
        md_lines.append("全部安全扫描通过。")

    md_path = output_dir / "security_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return overall


# ──────────────────────────────────────────────
# 6. CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="安全扫描编排脚本")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output-dir", default=None, help="报告输出目录（默认 .ai/evidence/security/）")
    parser.add_argument("--json", action="store_true", help="同时输出 JSON 到 stdout")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output_dir) if args.output_dir else project_root / ".ai" / "evidence" / "security"

    if not project_root.is_dir():
        print(json.dumps({"error": f"项目目录不存在: {project_root}"}))
        sys.exit(EXIT_BLOCK)

    print(f"[run_security_scan] 项目: {project_root}", file=sys.stderr)

    scans: List[Dict[str, Any]] = []

    # 1. 依赖 CVE 扫描
    print("[run_security_scan] 1/4 依赖 CVE 扫描...", file=sys.stderr)
    dep_scan = run_dependency_scan(project_root)
    scans.append(dep_scan)

    # 2. 密钥泄露扫描
    print("[run_security_scan] 2/4 密钥泄露扫描...", file=sys.stderr)
    secret_scan = run_secret_scan(project_root)
    scans.append(secret_scan)

    # 3. 注入面检测
    print("[run_security_scan] 3/4 注入面检测...", file=sys.stderr)
    injection_scan = run_injection_scan(project_root)
    scans.append(injection_scan)

    # 4. 权限模型审计
    print("[run_security_scan] 4/4 权限模型审计...", file=sys.stderr)
    perm_scan = run_permission_audit(project_root)
    scans.append(perm_scan)

    # 生成报告
    overall = generate_report(scans, project_root, output_dir)

    if args.json:
        json_report = output_dir / "security_report.json"
        if json_report.exists():
            print(json_report.read_text(encoding="utf-8"))

    if overall == "BLOCKED":
        blocked = [s["name"] for s in scans if s.get("status") == "blocked"]
        print(f"\n[run_security_scan] BLOCKED — {len(blocked)} 个扫描项未通过:", file=sys.stderr)
        for b in blocked:
            print(f"  - {b}", file=sys.stderr)
        sys.exit(EXIT_BLOCK)
    else:
        print("\n[run_security_scan] PASS — 全部安全扫描通过")
        sys.exit(EXIT_PASS)


if __name__ == "__main__":
    main()
