"""输入验证规则 (IV-001 ~ IV-006)。

检测 AI 常见的输入处理缺陷：无类型注解、无校验、注入漏洞等。
"""

import ast
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


def RULE_IV_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """公共函数参数无类型注解 — AI 偷懒。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith('_'):  # 公开函数
                missing = []
                for arg in node.args.args:
                    if arg.arg != 'self' and arg.arg != 'cls' and arg.annotation is None:
                        missing.append(arg.arg)
                if missing:
                    violations.append(Medium(
                        f"{node.name}(): 参数缺少类型注解: {', '.join(missing)}",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation=f"为参数添加类型注解"))
    return violations


def RULE_IV_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """字符串直接用于路径拼接 — AI 路径遍历漏洞。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # 字符串拼接
            left_is_str = (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str))
            right_is_var = isinstance(node.right, ast.Name)
            # 检查是否涉及路径
            if left_is_str and right_is_var:
                if '/' in str(node.left.value) or '\\' in str(node.left.value) or 'path' in str(node.left.value).lower():
                    violations.append(High(
                        f"路径拼接可能引入路径遍历漏洞",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="使用 os.path.join() 并对用户输入做校验"))
    return violations


def RULE_IV_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """SQL 字符串拼接 — AI 注入漏洞。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            left = node.left
            if isinstance(left, ast.Constant) and isinstance(left.value, str):
                sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                                'DROP', 'ALTER', 'FROM', 'WHERE', 'JOIN']
                if any(kw in left.value.upper() for kw in sql_keywords):
                    violations.append(Blocker(
                        f"SQL 字符串拼接 — 可能导致 SQL 注入",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="使用参数化查询: cursor.execute(sql, params)"))
        # 也检查 f-string 中的 SQL
        if isinstance(node, ast.JoinedStr):
            full_text = ''
            for part in node.values:
                if isinstance(part, ast.Constant):
                    full_text += str(part.value)
            if any(kw in full_text.upper() for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                violations.append(Blocker(
                    f"f-string SQL 拼接 — SQL 注入风险",
                    file_path=file_path, line=node.lineno,
                    snippet=full_text[:80],
                    remediation="使用参数化查询"))
    return violations


def RULE_IV_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """数值参数无范围检查 — AI 没考虑边界。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation and isinstance(arg.annotation, ast.Name):
                    # 数值类型的参数应该有范围检查
                    pass  # 太难静态判断，跳过
    return violations


def RULE_IV_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """Optional 参数直接使用无 None 检查 — AI 忘记 null 安全。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            optional_params = set()
            for arg in node.args.args:
                if arg.annotation and isinstance(arg.annotation, ast.Subscript):
                    type_name = getattr(arg.annotation.value, 'id', '')
                    if type_name == 'Optional':
                        optional_params.add(arg.arg)
            # 检查函数体内是否对这些参数做了 None 检查
            if optional_params:
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                        if child.value.id in optional_params:
                            # 使用 .attr 之前应该先检查 None
                            in_check = False
                            for ancestor in ast.walk(node):
                                if isinstance(ancestor, ast.If):
                                    test_str = ast.unparse(ancestor.test) if hasattr(ast, 'unparse') else ''
                                    if f'{child.value.id} is None' in test_str or f'{child.value.id} is not None' in test_str:
                                        in_check = True
                                        break
                            if not in_check:
                                violations.append(Medium(
                                    f"{child.value.id} 是 Optional 类型但使用前未检查 None",
                                    file_path=file_path, line=child.lineno,
                                    remediation=f"添加 if {child.value.id} is not None 检查"))
    return violations


def RULE_IV_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """字典 key 直接访问 — AI KeyError 隐患。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                # dict['key'] 直接访问
                if isinstance(node.value, ast.Name):
                    violations.append(Medium(
                        f"字典直接下标访问 {node.value.id}['{node.slice.value}'] — 可能 KeyError",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation=f"使用 {node.value.id}.get('{node.slice.value}') 或检查 key 存在性"))
    return violations
