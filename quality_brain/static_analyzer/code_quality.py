"""代码质量规则 (CQ-001 ~ CQ-010)。

检测函数复杂度、可变默认参数、缺少文档等问题。
"""

import ast
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


def _count_nesting(node: ast.AST, depth: int = 0) -> int:
    """计算节点的最大嵌套深度。"""
    max_depth = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With,
                              ast.ExceptHandler, ast.FunctionDef, ast.ClassDef)):
            max_depth = max(max_depth, _count_nesting(child, depth + 1))
        else:
            max_depth = max(max_depth, _count_nesting(child, depth))
    return max_depth


def RULE_CQ_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数超过 8 个参数。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            param_count = len([a for a in node.args.args if a.arg not in ('self', 'cls')])
            if param_count > 8:
                violations.append(Medium(
                    f"{node.name}() 有 {param_count} 个参数 — 太多，考虑重构",
                    file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation="使用数据类或配置对象封装相关参数"))
    return violations


def RULE_CQ_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数超过 50 行。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                violations.append(Low(
                    f"{node.name}() 有 {length} 行 — 考虑拆分",
                    file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation=f"将 {node.name}() 拆分为更小的函数"))
    return violations


def RULE_CQ_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """嵌套深度超过 4 层。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            depth = _count_nesting(node)
            if depth > 4:
                violations.append(Medium(
                    f"{node.name}() 嵌套深度 {depth} 超过 4 层 — 考虑提取或提前 return",
                    file_path=file_path, line=node.lineno,
                    remediation="使用 guard clause 或提取嵌套逻辑到辅助函数"))
    return violations


def RULE_CQ_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """类超过 300 行。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 300:
                violations.append(Low(
                    f"{node.name} 类有 {length} 行 — 考虑拆分",
                    file_path=file_path, line=node.lineno,
                    remediation=f"将 {node.name} 拆分为更小的类"))
    return violations


def RULE_CQ_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数名过于相似 — 可能造成混淆。"""
    violations = []
    func_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_names.append((node.name, node.lineno))
    # 简单检查：Levenshtein 距离 < 3
    for i, (name1, line1) in enumerate(func_names):
        for name2, line2 in func_names[i + 1:]:
            if len(name1) > 3 and len(name2) > 3:
                if name1 != name2:
                    # 简单相似度检查
                    common = sum(1 for a, b in zip(name1, name2) if a == b)
                    if common >= len(name1) - 2 and common >= len(name2) - 2:
                        if abs(len(name1) - len(name2)) <= 2:
                            violations.append(Low(
                                f"函数名过于相似: {name1}() vs {name2}()",
                                file_path=file_path, line=line1,
                                remediation="使用更明确的函数名区分两者"))
    return violations


def RULE_CQ_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """类方法缺少 self/cls。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    if not child.name.startswith('__') or child.name == '__init__':
                        continue
                    # 检查是否是 staticmethod
                    is_static = any(
                        isinstance(d, ast.Name) and d.id == 'staticmethod'
                        for d in child.decorator_list
                    )
                    if not is_static:
                        args = child.args.args
                        if not args:
                            violations.append(High(
                                f"{child.name}(): 类方法缺少 self 参数",
                                file_path=file_path, line=child.lineno,
                                remediation="添加 self 作为第一个参数"))
    return violations


def RULE_CQ_007(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """可变默认参数（list/dict/set）。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    violations.append(High(
                        f"{node.name}(): 可变默认参数 — 所有调用共享同一对象",
                        file_path=file_path, line=default.lineno,
                        snippet=_get_line(source, default.lineno),
                        remediation="使用 None 作为默认值，函数体内初始化: if x is None: x = []"))
    return violations


def RULE_CQ_008(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """条件判断中的赋值 = 而非 =="""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) or isinstance(node, ast.While):
            if isinstance(node.test, ast.NamedExpr):
                # := (海象运算符) 是 Python 3.8+ 的有意行为
                pass
            elif isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                pass  # not x = ... 不会被误判
    return violations


def RULE_CQ_009(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """公开函数无 docstring。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith('_'):
                docstring = ast.get_docstring(node)
                if not docstring:
                    violations.append(Low(
                        f"{node.name}(): 缺少 docstring",
                        file_path=file_path, line=node.lineno,
                        remediation="添加简要的 docstring 说明函数用途"))
    return violations


def RULE_CQ_010(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """同一行多个语句（分号分隔）。"""
    violations = []
    for i, line in enumerate(source.split('\n'), 1):
        stripped = line.strip()
        if ';' in stripped and not stripped.startswith('#') and not stripped.startswith('import'):
            # 排除字符串内的分号
            in_string = False
            semicolon_count = 0
            for ch in stripped:
                if ch in ('"', "'"):
                    in_string = not in_string
                elif ch == ';' and not in_string:
                    semicolon_count += 1
            if semicolon_count > 0:
                violations.append(Low(
                    f"同一行 {semicolon_count+1} 个语句（分号分隔）",
                    file_path=file_path, line=i,
                    snippet=stripped[:80],
                    remediation="将语句分开到不同行"))
    return violations
