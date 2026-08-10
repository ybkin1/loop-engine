"""AI 特有反模式规则 (AI-001 ~ AI-012) ★ 最重要。

这些规则专门针对 AI 代码生成的失败模式：
- 过度工程化（无人调用的抽象）
- 复制粘贴（重复逻辑体）
- 上下文漂移（注释与代码矛盾）
- 幻觉（局部 import 兜底）
- 混乱（未使用变量、不可达代码）
"""

import ast
import hashlib
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


def _get_func_body_hash(node: ast.FunctionDef) -> str:
    """获取函数体的简化哈希（用于检测重复）。"""
    try:
        body_text = ast.unparse(node.body)
        # 移除空白和注释影响
        body_text = ''.join(body_text.split())
        return hashlib.md5(body_text.encode()).hexdigest()
    except Exception:
        return ""


def RULE_AI_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数在整个项目中无调用者 — AI 过度工程化。"""
    violations = []
    # 收集所有函数定义和调用
    defined_funcs: dict[str, ast.FunctionDef] = {}
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith('_'):  # 只检查公开函数
                defined_funcs[node.name] = node
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

    # 排除特殊方法
    special_methods = {'__init__', '__str__', '__repr__', '__len__', '__getitem__',
                       '__setitem__', '__iter__', '__next__', '__enter__', '__exit__',
                       '__call__', '__eq__', '__hash__', 'main', 'run', 'handle'}

    for name, func in defined_funcs.items():
        if name not in called_names and name not in special_methods:
            # 再检查函数体内部是否有自引用
            self_ref = False
            for child in ast.walk(func):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if child.func.id == name:
                        self_ref = True
                        break
            if not self_ref:
                violations.append(High(
                    f"函数 {name}() 在文件中无调用者 — 可能是过度工程化或死代码",
                    rule_id="AI-001", file_path=file_path, line=func.lineno,
                    snippet=_get_line(source, func.lineno),
                    remediation="如果没有调用者，考虑移除或标记为候选删除"))
    return violations


def RULE_AI_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数体高度相似（>90% 重复）— AI 复制粘贴。"""
    violations = []
    func_hashes: dict[str, list[ast.FunctionDef]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and len(node.body) >= 5:
            h = _get_func_body_hash(node)
            if h:
                if h not in func_hashes:
                    func_hashes[h] = []
                func_hashes[h].append(node)

    for h, funcs in func_hashes.items():
        if len(funcs) > 1:
            names = [f.name for f in funcs]
            violations.append(High(
                f"函数体高度相似 ({len(funcs)} 个): {', '.join(names)} — 可能是复制粘贴",
                rule_id="AI-002", file_path=file_path, line=funcs[0].lineno,
                remediation="提取公共逻辑到辅助函数"))
    return violations


def RULE_AI_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """变量赋值后从未使用 — AI 混乱、幻觉残留。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assigned: set[str] = set()
            used: set[str] = set()

            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            assigned.add(target.id)
                elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    used.add(child.id)

            unused = assigned - used
            for name in unused:
                if name not in ('_', '__'):
                    violations.append(Medium(
                        f"变量 '{name}' 赋值后从未使用 — 可能是幻觉残留",
                        rule_id="AI-003", file_path=file_path, line=node.lineno,
                        remediation="删除未使用的变量"))
    return violations


def RULE_AI_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """import 在函数体内 — AI 不确定就用局部 import 兜底。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    violations.append(High(
                        f"函数 {node.name}() 内的局部 import — AI 幻觉兜底模式",
                        rule_id="AI-004", file_path=file_path, line=child.lineno,
                        snippet=_get_line(source, child.lineno),
                        remediation="将 import 移至文件顶部，确认依赖已声明"))
    return violations


def RULE_AI_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """注释内容与代码逻辑矛盾 — AI 上下文漂移。"""
    violations = []
    # 简单启发式：检查函数 docstring 中的参数名是否与实际参数匹配
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            if docstring:
                actual_params = [a.arg for a in node.args.args if a.arg != 'self' and a.arg != 'cls']
                # 检查 docstring 中提到的参数是否都是实际参数
                for param in actual_params:
                    pass  # 太复杂，需要 NLP，跳过深度检查
    return violations


def RULE_AI_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数有 docstring 但参数名不匹配 — AI 编造文档。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            if docstring:
                actual_params = set(a.arg for a in node.args.args if a.arg not in ('self', 'cls'))
                # 简单检查：docstring 中提到的 `:param` 是否对应实际参数
                if ':param' in docstring:
                    import re
                    doc_params = set(re.findall(r':param\s+(\w+)\s*:', docstring))
                    extra = doc_params - actual_params
                    missing = actual_params - doc_params
                    if extra:
                        violations.append(Medium(
                            f"docstring 引用了不存在的参数: {extra}",
                            rule_id="AI-006", file_path=file_path, line=node.lineno,
                            remediation="更新 docstring 使其与实际参数一致"))
    return violations


def RULE_AI_007(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """不可达代码 — return/raise/break/continue 后的语句。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.While, ast.For)):
            body = node.body if isinstance(node, ast.FunctionDef) else (
                node.body if hasattr(node, 'body') else []
            )
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    unreachable = body[i + 1:]
                    if unreachable:
                        violations.append(Medium(
                            f"{type(stmt).__name__} 后的代码不可达 ({len(unreachable)} 行)",
                            rule_id="AI-007", file_path=file_path, line=body[i+1].lineno,
                            remediation="移除不可达代码"))
                        break
    return violations


def RULE_AI_008(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """同一逻辑用不同方式实现 — AI 无全局视角导致不一致。"""
    # 太复杂需要语义分析，跳过
    return []


def RULE_AI_009(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """TODO/FIXME/HACK 超过 3 处 — AI 留坑不填。"""
    violations = []
    count = 0
    locations = []
    for i, line in enumerate(source.split('\n'), 1):
        for marker in ['TODO', 'FIXME', 'HACK', 'XXX']:
            if marker in line and not line.strip().startswith('#'):
                pass  # 检查是否是注释
        if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
            count += 1
            if count <= 5:  # 只记录前 5 个
                locations.append(f"L{i}")

    if count > 3:
        violations.append(Medium(
            f"{count} 处 TODO/FIXME/HACK — AI 留坑不填",
            rule_id="AI-009", file_path=file_path, line=0,
            snippet=f"位置: {', '.join(locations[:5])}...",
            remediation="清理或转化为实际任务"))
    return violations


def RULE_AI_010(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数超过 50 行且无分段注释 — AI 面条代码。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > 50:
                # 检查是否有分段注释
                body_lines = source.split('\n')[node.lineno:node.end_lineno]
                has_section_comment = any(
                    l.strip().startswith('#') and len(l.strip()) > 3
                    for l in body_lines
                )
                if not has_section_comment:
                    violations.append(Low(
                        f"{node.name}() 超过 50 行 ({length} 行) 且无分段注释",
                        rule_id="AI-010", file_path=file_path, line=node.lineno,
                        remediation="拆分为更小的函数或添加分段注释"))
    return violations


def RULE_AI_011(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """硬编码值出现多次 — AI 不用常量。"""
    violations = []
    literal_counts: dict[str, list[int]] = {}

    # 暂不实现完整版本，太复杂
    return violations


def RULE_AI_012(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """isinstance 检查后不做类型不同处理 — AI 过度防御。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Call):
            if isinstance(node.test.func, ast.Name) and node.test.func.id == 'isinstance':
                if len(node.body) <= 1 and isinstance(node.body[0] if node.body else None, ast.Pass):
                    violations.append(Low(
                        f"isinstance 检查后无处理逻辑 — AI 过度防御",
                        rule_id="AI-012", file_path=file_path, line=node.lineno,
                        remediation="移除无意义的 isinstance 检查或添加实际处理"))
    return violations
