"""错误处理规则 (EH-001 ~ EH-008)。

检测 AI 常见的错误处理偷懒模式：裸 except、静默吞异常、资源泄漏等。
"""

import ast
from quality_brain.core import Violation, Severity, Blocker, High, Medium, Low


def _get_line(source: str, lineno: int) -> str:
    lines = source.split('\n')
    if 0 <= lineno - 1 < len(lines):
        return lines[lineno - 1].strip()
    return ""


def RULE_EH_001(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """裸 except: 或 except Exception: — AI 偷懒，一把抓。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                violations.append(High(
                    f"裸 except: — 应指定具体异常类型",
                    file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation="指定具体异常类型，如 except ValueError as e:"))
            elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                violations.append(High(
                    f"except Exception: — 范围太宽，应指定具体异常",
                    file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation="使用更具体的异常类型"))
    return violations


def RULE_EH_002(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """except: pass — AI 致命静默吞异常。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                violations.append(Blocker(
                    f"except: pass — 静默吞异常，可能导致关键错误被忽略",
                    file_path=file_path, line=node.lineno,
                    snippet=_get_line(source, node.lineno),
                    remediation="至少记录日志: except X as e: logger.error(...)"))
            # 另外检查 except Exception: pass
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass) and node.type:
                if isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                    violations.append(Blocker(
                        f"except Exception: pass — 致命静默",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="至少记录日志或重新抛出"))
    return violations


def RULE_EH_003(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """函数含 try/except 但无 return/raise — AI 忘记处理异常路径。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
            has_return = any(isinstance(n, ast.Return) and n.value is not None
                           for n in ast.walk(node))
            has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(node))
            if has_try and not has_return and not has_raise:
                # 检查函数是否确实应该有返回值（有类型注解暗示）
                if node.returns or any(
                    isinstance(n, ast.Return) for n in ast.walk(node)
                ):
                    violations.append(High(
                        f"{node.name}(): 有异常路径但可能缺少 return",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="确保异常路径也有明确的返回值或 raise"))
    return violations


def RULE_EH_004(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """open() 无 with 或无 close() — AI 泄漏资源。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'open':
                # 检查是否在 with 语句中
                parent = getattr(node, '_parent', None)
                in_with = False
                for ancestor in ast.walk(tree):
                    if isinstance(ancestor, ast.With):
                        for item in ancestor.items:
                            if item.context_expr == node:
                                in_with = True
                                break
                if not in_with:
                    violations.append(High(
                        f"open() 未使用 with 语句 — 可能导致文件句柄泄漏",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="使用 with open(...) as f: 确保自动关闭"))
    return violations


def RULE_EH_005(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """requests.get/post 无 timeout — AI 默认行为可能导致永久挂起。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ''
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
            if func_name in ('get', 'post', 'put', 'delete', 'patch', 'request'):
                # 检查是否传了 timeout
                has_timeout = False
                for kw in node.keywords:
                    if kw.arg == 'timeout':
                        has_timeout = True
                        break
                if not has_timeout:
                    violations.append(Medium(
                        f"{func_name}() 缺少 timeout 参数 — 网络请求可能永久挂起",
                        file_path=file_path, line=node.lineno,
                        snippet=_get_line(source, node.lineno),
                        remediation="添加 timeout=30 参数"))
    return violations


def RULE_EH_006(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """except 块中 logger.error 但未包含异常信息 — AI 敷衍日志。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            log_calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if child.func.attr in ('error', 'warning', 'exception', 'critical'):
                            log_calls.append(child)
            for call in log_calls:
                has_exc_info = any(
                    kw.arg == 'exc_info' and (
                        (isinstance(kw.value, ast.Constant) and kw.value.value is True)
                    )
                    for kw in call.keywords
                )
                has_exc_arg = any(
                    isinstance(arg, ast.Name)
                    for arg in call.args + [kw.value for kw in call.keywords if kw.arg != 'exc_info']
                )
                if not has_exc_info and not has_exc_arg:
                    violations.append(Medium(
                        f"except 块中的日志未包含异常信息",
                        file_path=file_path, line=call.lineno or node.lineno,
                        snippet=_get_line(source, call.lineno or node.lineno),
                        remediation="使用 logger.error(..., exc_info=True) 或 logger.exception(...)"))
    return violations


def RULE_EH_007(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """重试循环无最大次数 — AI 可能创建无限循环。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body_text = source[node.body[0].lineno - 1:node.body[-1].end_lineno] if node.body else ""
            if 'retry' in body_text.lower() or '重试' in body_text:
                has_max = any('max_' in source[node.lineno:node.end_lineno] for _ in [1])
                if not has_max:
                    violations.append(Medium(
                        f"重试逻辑可能缺少最大重试次数限制",
                        file_path=file_path, line=node.lineno,
                        remediation="添加 max_retries 计数器并在超限时 raise"))
    return violations


def RULE_EH_008(tree: ast.AST, source: str, file_path: str) -> list[Violation]:
    """except 块中 bare raise — AI 丢失原始异常信息。"""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for child in ast.walk(node):
                if isinstance(child, ast.Raise):
                    if child.exc is None:
                        pass  # bare raise 重新抛出当前异常，这是 OK 的
                    elif isinstance(child.exc, ast.Call):
                        # raise NewException(...) — 检查是否包含原始异常
                        if not any(
                            isinstance(arg, ast.Name)
                            for arg in child.exc.args
                        ):
                            violations.append(Medium(
                                f"raise 新异常时未包含原始异常 — 丢失调试信息",
                                file_path=file_path, line=child.lineno,
                                remediation="使用 raise NewException(...) from e"))
    return violations
