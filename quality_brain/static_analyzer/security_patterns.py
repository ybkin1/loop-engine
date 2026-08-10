"""安全模式规则 (SE-001 ~ SE-008)。

检测硬编码密钥、注入点、不安全反序列化等安全漏洞。
"""

import ast
import re
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


# ── 硬编码密钥检测 ──
_SECRET_PATTERNS = [
    (re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{6,})["\']', re.IGNORECASE), 'password'),
    (re.compile(r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE), 'API key'),
    (re.compile(r'(?:secret[_-]?key|secretkey)\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE), 'secret key'),
    (re.compile(r'(?:access[_-]?token|accesstoken)\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE), 'access token'),
    (re.compile(r'ghp_[A-Za-z0-9]{36}'), 'GitHub token'),
    (re.compile(r'sk-[A-Za-z0-9]{32,}'), 'OpenAI key'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS access key'),
    (re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'), 'private key'),
    (re.compile(r'(?:token|auth)\s*[:=]\s*["\']([^"\']{16,})["\']', re.IGNORECASE), 'auth token'),
]

# 排除模式（占位符、示例值）
_EXCLUDE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'your[_-]', r'example', r'placeholder', r'changeme', r'dummy',
        r'<your', r'<password>', r'xxxx', r'\*\*\*\*', r'\${', r'%s',
        r'os\.environ', r'os\.getenv', r'config\[', r'settings\.',
        r'YOUR_', r'my[_-]', r'test[_-]', r'sample', r'demo', r'fake',
    ]
]


def RULE_SE_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """硬编码密码/API key/Token。"""
    violations = []
    for i, line in enumerate(source.split('\n'), 1):
        # 跳过注释行
        if line.strip().startswith('#') or line.strip().startswith('//'):
            continue
        # 跳过排除模式
        excluded = False
        for pat in _EXCLUDE_PATTERNS:
            if pat.search(line):
                excluded = True
                break
        if excluded:
            continue

        for pattern, label in _SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                # 进一步检查：捕获的值不能是明显的占位符
                captured = match.group(1) if match.lastindex else ''
                if captured and len(captured) < 6:
                    continue  # 太短，可能是变量名
                violations.append(Blocker(
                    f"疑似硬编码 {label}: {line.strip()[:80]}",
                    rule_id="SE-001", file_path=file_path, line=i,
                    snippet=line.strip()[:80],
                    remediation=f"将 {label} 移至环境变量或配置文件"))
    return violations


def RULE_SE_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """os.system() 或 subprocess(shell=True) — 命令注入风险。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # os.system()
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'system':
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                        violations.append(High(
                            f"os.system() — 命令注入风险",
                            rule_id="SE-002", file_path=file_path, line=node.lineno,
                            snippet=_get_line(source, node.lineno),
                            remediation="使用 subprocess.run([cmd, arg1, arg2])"))
            # subprocess(..., shell=True)
            if isinstance(node.func, ast.Name) and node.func.id in ('call', 'run', 'Popen', 'check_output'):
                for kw in node.keywords:
                    if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        violations.append(High(
                            f"subprocess 使用 shell=True — 命令注入风险",
                            rule_id="SE-002", file_path=file_path, line=node.lineno,
                            snippet=_get_line(source, node.lineno),
                            remediation="移除 shell=True，使用列表参数"))
    return violations


def RULE_SE_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """eval() / exec() 的动态参数。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ('eval', 'exec'):
                    # 检查参数是否是动态的（非常量）
                    if node.args:
                        arg = node.args[0]
                        if not isinstance(arg, ast.Constant):
                            violations.append(Blocker(
                                f"{node.func.id}() 使用动态参数 — 代码注入风险",
                                rule_id="SE-003", file_path=file_path, line=node.lineno,
                                snippet=_get_line(source, node.lineno),
                                remediation="避免使用 eval/exec，寻找安全的替代方案"))
    return violations


def RULE_SE_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """pickle.load() 不可信数据。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ('load', 'loads'):
                    if isinstance(node.func.value, ast.Name) and 'pickle' in node.func.value.id.lower():
                        violations.append(High(
                            f"pickle.load() — 反序列化不可信数据风险",
                            rule_id="SE-004", file_path=file_path, line=node.lineno,
                            snippet=_get_line(source, node.lineno),
                            remediation="使用 JSON 或限制 pickle 的反序列化范围"))
    return violations


def RULE_SE_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """yaml.load() 非 SafeLoader。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'load' and isinstance(node.func.value, ast.Name):
                    if 'yaml' in node.func.value.id.lower():
                        # 检查是否使用了 SafeLoader
                        has_safe_loader = False
                        for kw in node.keywords:
                            if kw.arg == 'Loader':
                                if isinstance(kw.value, ast.Attribute) and 'Safe' in kw.value.attr:
                                    has_safe_loader = True
                        if not has_safe_loader:
                            violations.append(High(
                                f"yaml.load() 未使用 SafeLoader",
                                rule_id="SE-005", file_path=file_path, line=node.lineno,
                                snippet=_get_line(source, node.lineno),
                                remediation="使用 yaml.safe_load() 或 yaml.load(..., Loader=yaml.SafeLoader)"))
    return violations


def RULE_SE_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """SQL 拼接（f-string/format/+）"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ''
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in ('execute', 'executemany'):
                for arg in node.args:
                    if isinstance(arg, (ast.JoinedStr, ast.BinOp)):
                        violations.append(Blocker(
                            f"SQL 执行使用字符串拼接 — SQL 注入风险",
                            rule_id="SE-006", file_path=file_path, line=node.lineno,
                            snippet=_get_line(source, node.lineno),
                            remediation="使用参数化查询: cursor.execute(sql, (param1, param2))"))
    return violations


def RULE_SE_007(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """assert 用于业务逻辑校验 — 生产环境可能被禁用。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            # 排除测试文件
            if 'test' not in file_path.lower():
                violations.append(Medium(
                    f"assert 用于业务逻辑 — 生产环境中 -O 模式会跳过",
                    rule_id="SE-007", file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation="使用 if not condition: raise ValueError(...)"))
    return violations


def RULE_SE_008(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """日志中输出敏感字段 — 信息泄露。"""
    violations = []
    sensitive_fields = {'password', 'passwd', 'pwd', 'token', 'secret', 'key',
                        'api_key', 'apikey', 'credential', 'private_key'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ('debug', 'info', 'warning', 'error', 'critical', 'log'):
                    # 检查参数中是否包含敏感字段名
                    for arg in node.args + [kw.value for kw in node.keywords]:
                        if isinstance(arg, ast.Name) and arg.id.lower() in sensitive_fields:
                            violations.append(High(
                                f"日志中可能输出敏感字段: {arg.id}",
                                rule_id="SE-008", file_path=file_path, line=node.lineno,
                                snippet=_get_line(source, node.lineno),
                                remediation="日志中不要输出敏感信息，或做脱敏处理"))
    return violations
