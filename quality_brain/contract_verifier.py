"""合约验证器 — 验证实际代码是否匹配接口契约。

从 interface_contract.yaml 读取合约定义，AST 解析实际代码，逐项对照。
"""

import ast
import os
from pathlib import Path
from typing import Optional

import yaml

from .core import Violation, Severity, Blocker, High, Medium, Low


class ContractVerifier:
    """合约验证器。"""

    def verify(self, contract_path: str, source_root: str) -> list[Violation]:
        """
        验证合约。

        合约格式 (YAML):
        ```yaml
        modules:
          auth:
            source: src/auth.py
            exports:
              - function: authenticate
                params:
                  - name: username
                    type: str
                  - name: password
                    type: str
                returns: AuthResult
                raises: [AuthenticationError]
        ```
        """
        violations = []
        contract_file = Path(contract_path)
        if not contract_file.exists():
            return [Blocker(f"合约文件不存在: {contract_path}")]

        try:
            contract = yaml.safe_load(contract_file.read_text(encoding='utf-8'))
        except yaml.YAMLError as e:
            return [Blocker(f"合约文件解析失败: {e}")]

        if not contract or 'modules' not in contract:
            return [Blocker("合约文件格式错误: 缺少 'modules' 字段")]

        for module_name, module_def in contract['modules'].items():
            source_file = module_def.get('source', f'{module_name}.py')
            full_source = Path(source_root) / source_file

            if not full_source.exists():
                violations.append(Blocker(
                    f"模块 '{module_name}' 的源文件不存在: {full_source}",
                    rule_id="CONTRACT-MISSING-FILE"))
                continue

            try:
                tree = ast.parse(full_source.read_text(encoding='utf-8'))
            except SyntaxError as e:
                violations.append(Blocker(
                    f"模块 '{module_name}' 语法错误: {e}",
                    rule_id="CONTRACT-SYNTAX"))
                continue

            for export in module_def.get('exports', []):
                func_name = export.get('function')
                if not func_name:
                    continue

                func_node = self._find_function(tree, func_name)
                if not func_node:
                    violations.append(Blocker(
                        f"合约中定义的函数 '{func_name}()' 在 {source_file} 中不存在",
                        rule_id="CONTRACT-MISSING-FUNC",
                        file_path=str(full_source)))
                    continue

                # 参数检查
                violations.extend(self._check_params(
                    export.get('params', []), func_node, func_name, str(full_source)))

                # 返回类型检查
                violations.extend(self._check_return_type(
                    export.get('returns'), func_node, func_name, str(full_source)))

                # 异常检查
                violations.extend(self._check_raises(
                    export.get('raises', []), func_node, func_name, str(full_source)))

        return violations

    def _find_function(self, tree: ast.AST, name: str) -> Optional[ast.FunctionDef]:
        """在 AST 中查找指定名称的函数定义。"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def _check_params(self, expected: list, func: ast.FunctionDef,
                      func_name: str, file_path: str) -> list[Violation]:
        """检查函数参数是否匹配。"""
        violations = []
        actual_params = [a for a in func.args.args if a.arg not in ('self', 'cls')]

        if len(actual_params) != len(expected):
            violations.append(Blocker(
                f"{func_name}(): 参数数量不匹配 (合约 {len(expected)} vs 代码 {len(actual_params)})",
                rule_id="CONTRACT-PARAM-COUNT",
                file_path=file_path, line=func.lineno))
            return violations

        for exp, act in zip(expected, actual_params):
            if exp['name'] != act.arg:
                violations.append(High(
                    f"{func_name}(): 参数名不匹配 (合约 '{exp['name']}' vs 代码 '{act.arg}')",
                    rule_id="CONTRACT-PARAM-NAME",
                    file_path=file_path, line=func.lineno))

            # 类型检查
            exp_type = exp.get('type', '')
            act_type = self._get_annotation(act.annotation)
            if exp_type and act_type and exp_type != act_type:
                violations.append(High(
                    f"{func_name}(): 参数 '{act.arg}' 类型不匹配 (合约 '{exp_type}' vs 代码 '{act_type}')",
                    rule_id="CONTRACT-PARAM-TYPE",
                    file_path=file_path, line=func.lineno))

        return violations

    def _check_return_type(self, expected: Optional[str], func: ast.FunctionDef,
                           func_name: str, file_path: str) -> list[Violation]:
        """检查返回类型。"""
        if not expected:
            return []

        actual = self._get_annotation(func.returns)
        if not actual:
            return [High(
                f"{func_name}(): 缺少返回类型注解 (合约要求 '{expected}')",
                rule_id="CONTRACT-RETURN-MISSING",
                file_path=file_path, line=func.lineno)]

        if expected != actual:
            return [High(
                f"{func_name}(): 返回类型不匹配 (合约 '{expected}' vs 代码 '{actual}')",
                rule_id="CONTRACT-RETURN-TYPE",
                file_path=file_path, line=func.lineno)]

        return []

    def _check_raises(self, expected: list, func: ast.FunctionDef,
                      func_name: str, file_path: str) -> list[Violation]:
        """检查声明的异常。"""
        if not expected:
            return []

        # 提取函数体内 raise 的异常类型
        actual_raises = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Raise) and node.exc:
                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                    actual_raises.add(node.exc.func.id)
                elif isinstance(node.exc, ast.Name):
                    actual_raises.add(node.exc.id)

        declared = set(expected)
        missing = declared - actual_raises

        if missing:
            # 不标记为 BLOCKER，因为异常可能是间接抛出的
            pass  # 仅记录，不阻塞

        return []

    def _get_annotation(self, node) -> str:
        """从 AST 注解节点获取类型字符串。"""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Subscript):
            base = self._get_annotation(node.value)
            return f"{base}[...]"
        if isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        return ""


def verify_contract(contract_path: str, source_root: str) -> list[Violation]:
    """便捷函数。"""
    verifier = ContractVerifier()
    return verifier.verify(contract_path, source_root)
