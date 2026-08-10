"""资源与性能规则 (RP-001 ~ RP-006)。

检测循环内查询、资源泄漏、低效模式等问题。
"""

import ast
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


def _is_inside_loop(node: ast.AST, tree: ast.AST) -> bool:
    """检查节点是否在循环内部。"""
    # 简化实现：检查父节点链
    # 由于 AST 默认不维护父节点引用，这里做一个近似检查
    # 通过 source lines 范围判断
    for ancestor in ast.walk(tree):
        if isinstance(ancestor, (ast.For, ast.While)):
            if hasattr(ancestor, 'end_lineno') and ancestor.end_lineno:
                if ancestor.lineno <= node.lineno <= ancestor.end_lineno and ancestor != node:
                    return True
    return False


def RULE_RP_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """循环内的数据库查询/HTTP 请求 — N+1 问题。"""
    violations = []
    db_methods = {'execute', 'executemany', 'fetchone', 'fetchall', 'fetchmany',
                  'get', 'post', 'put', 'delete', 'patch', 'request',
                  'find', 'find_one', 'find_all', 'query', 'filter'}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ''
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in db_methods:
                if _is_inside_loop(node, tree):
                    violations.append(High(
                        f"循环内调用 {func_name}() — 可能导致 N+1 查询或性能问题",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="将查询移到循环外，使用批量操作"))
    return violations


def RULE_RP_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """大列表用 + 拼接 — 应用 join/extend。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for child in ast.walk(node):
                if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                    if isinstance(child.target, ast.Name):
                        violations.append(Medium(
                            f"循环内 {child.target.id} += ... — 列表拼接效率低",
                            file_path=file_path, line=child.lineno,
                            snippet=_get_line(source, child.lineno),
                            remediation="使用 list.append() 或 ''.join()"))
    return violations


def RULE_RP_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """循环内 open() 无关闭。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for child in ast.walk(node):
                if isinstance(child, ast.With):
                    # with 语句自动关闭，没问题
                    break
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name) and child.func.id == 'open':
                        violations.append(High(
                            f"循环内 open() 文件操作 — 应移到循环外",
                            file_path=file_path, line=child.lineno,
                            snippet=_get_line(source, child.lineno),
                            remediation="在循环外打开文件，循环内处理"))
    return violations


def RULE_RP_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """递归函数无深度限制。"""
    violations = []
    recursive_funcs: dict[str, ast.FunctionDef] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # 检查函数是否调用自身
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if child.func.id == node.name:
                        recursive_funcs[node.name] = node
                        break

    for name, func in recursive_funcs.items():
        # 检查是否有深度限制参数
        has_depth_limit = False
        for arg in func.args.args:
            if 'depth' in arg.arg.lower() or 'limit' in arg.arg.lower() or 'max_' in arg.arg.lower():
                has_depth_limit = True
                break
        if not has_depth_limit:
            violations.append(High(
                f"{name}() 是递归函数但无深度限制参数 — 可能导致栈溢出",
                file_path=file_path, line=func.lineno,
                remediation="添加 depth 参数并在超限时 raise RecursionError"))
    return violations


def RULE_RP_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """range(len(x)) 而非 enumerate。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Call):
                if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                    if len(node.iter.args) == 1:
                        arg = node.iter.args[0]
                        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'len':
                            violations.append(Low(
                                f"range(len(...)) — 使用 enumerate() 更 Pythonic",
                                file_path=file_path, line=node.lineno,
                                snippet=_get_line(source, node.lineno),
                                remediation="使用 for i, item in enumerate(items):"))
    return violations


def RULE_RP_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """if x in list — 应用 if x in set。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if isinstance(node.ops[0], ast.In) if node.ops else False:
                for comparator in node.comparators:
                    if isinstance(comparator, ast.List):
                        violations.append(Medium(
                            f"if x in list — 使用 set 查找更快 (O(1) vs O(n))",
                            file_path=file_path, line=node.lineno,
                            snippet=_get_line(source, node.lineno),
                            remediation="将列表转为 set: MY_SET = {...}; if x in MY_SET:"))
    return violations
