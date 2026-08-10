"""架构合规扫描器 — 检测代码是否违反分层架构和依赖规则。"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml

from .core import Violation, Severity, Blocker, High, Medium, Low


class ArchitectureScanner:
    """架构合规扫描器。"""

    def __init__(self):
        self._layer_map: dict[str, str] = {}  # 文件路径 → 层名
        self._rules: dict = {}

    def load_architecture(self, arch_path: str) -> list[Violation]:
        """加载架构定义文件。"""
        violations = []
        arch_file = Path(arch_path)
        if not arch_file.exists():
            return [Blocker(f"架构文件不存在: {arch_path}")]

        try:
            arch = yaml.safe_load(arch_file.read_text(encoding='utf-8'))
        except yaml.YAMLError as e:
            return [Blocker(f"架构文件解析失败: {e}")]

        if not arch:
            return []

        # 解析分层定义
        self._rules = arch
        self._layer_map = {}

        for layer in arch.get('layers', []):
            layer_name = layer.get('name', '')
            for path_pattern in layer.get('paths', []):
                self._layer_map[path_pattern] = layer_name

        return violations

    def scan(self, source_root: str) -> list[Violation]:
        """扫描整个源码目录，检测架构违规。"""
        violations = []

        # 构建导入图
        import_graph = self._build_import_graph(source_root)

        # 检查 1：分层违规
        violations.extend(self._check_layer_violations(import_graph))

        # 检查 2：循环依赖
        violations.extend(self._check_circular_deps(import_graph))

        # 检查 3：禁止模式
        violations.extend(self._check_forbidden_patterns(source_root))

        return violations

    def _build_import_graph(self, source_root: str) -> dict:
        """构建模块导入图。"""
        graph = {
            'nodes': {},      # module_name -> {file, layer, imports}
            'edges': [],      # (from_module, to_module, lineno)
        }

        for dirpath, _, filenames in os.walk(source_root):
            if any(skip in dirpath for skip in ['__pycache__', '.venv', 'venv', 'node_modules', '.git']):
                continue
            for fname in filenames:
                if fname.endswith('.py'):
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, source_root)
                    module_name = rel_path.replace('/', '.').replace('\\', '.').replace('.py', '')

                    try:
                        source = Path(full_path).read_text(encoding='utf-8')
                        tree = ast.parse(source)
                    except Exception:
                        continue

                    imports = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.append((alias.name, node.lineno))
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.append((node.module, node.lineno))

                    layer = self._classify_file(rel_path)
                    graph['nodes'][module_name] = {
                        'file': rel_path,
                        'layer': layer,
                    }

                    for imp, lineno in imports:
                        graph['edges'].append((module_name, imp, lineno))

        return graph

    def _classify_file(self, rel_path: str) -> str:
        """根据文件路径判断所属层。"""
        for pattern, layer in self._layer_map.items():
            if pattern in rel_path or rel_path.startswith(pattern):
                return layer
        return 'unknown'

    def _check_layer_violations(self, graph: dict) -> list[Violation]:
        """检查分层违规（底层 import 上层、禁止依赖）。"""
        violations = []

        if not self._rules:
            return violations

        # 构建层的禁止依赖映射
        forbidden: dict[str, set[str]] = {}
        for layer in self._rules.get('layers', []):
            name = layer.get('name', '')
            forbidden[name] = set(layer.get('forbidden_deps', []))

        for from_mod, to_mod, lineno in graph['edges']:
            from_info = graph['nodes'].get(from_mod, {})
            to_info = graph['nodes'].get(to_mod, {})

            from_layer = from_info.get('layer', 'unknown')
            to_layer = to_info.get('layer', 'unknown')

            if from_layer in forbidden:
                if to_layer in forbidden[from_layer]:
                    violations.append(High(
                        f"跨层依赖违规: {from_mod} ({from_layer}) → {to_mod} ({to_layer})",
                        rule_id="ARCH-LAYER",
                        file_path=from_info.get('file', from_mod),
                        line=lineno,
                        remediation=f"{from_layer} 不应依赖 {to_layer}"))

        return violations

    def _check_circular_deps(self, graph: dict) -> list[Violation]:
        """检查循环依赖。"""
        violations = []
        adj: dict[str, set[str]] = defaultdict(set)

        for from_mod, to_mod, _ in graph['edges']:
            adj[from_mod].add(to_mod)

        # DFS 检测循环
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.discard(node)

        for node in graph['nodes']:
            if node not in visited:
                dfs(node, [])

        for cycle in cycles:
            if len(cycle) > 2:  # 忽略自引用
                violations.append(Blocker(
                    f"循环依赖: {' → '.join(cycle)}",
                    rule_id="ARCH-CIRCULAR"))

        return violations

    def _check_forbidden_patterns(self, source_root: str) -> list[Violation]:
        """检查禁止的代码模式。"""
        violations = []
        patterns = self._rules.get('forbidden_patterns', [])

        for dirpath, _, filenames in os.walk(source_root):
            if any(skip in dirpath for skip in ['__pycache__', '.venv', 'venv']):
                continue
            for fname in filenames:
                if fname.endswith('.py'):
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, source_root)
                    try:
                        source = Path(full_path).read_text(encoding='utf-8')
                    except Exception:
                        continue

                    for i, line in enumerate(source.split('\n'), 1):
                        for pattern in patterns:
                            if isinstance(pattern, str) and pattern in line:
                                violations.append(High(
                                    f"禁止模式: {pattern}",
                                    rule_id="ARCH-PATTERN",
                                    file_path=rel_path, line=i,
                                    snippet=line.strip()[:80]))
        return violations


def scan_architecture(architecture_path: str, source_root: str) -> list[Violation]:
    """便捷函数。"""
    scanner = ArchitectureScanner()
    violations = scanner.load_architecture(architecture_path)
    if violations:
        return violations
    return scanner.scan(source_root)
