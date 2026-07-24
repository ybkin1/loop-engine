#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_dependencies.py — 依赖分析工具（系统架构师使用）。

确定性代码，不依赖 LLM。检测项目模块间的循环依赖与边界违规。
优先使用 madge（JS/TS 项目），不可用时回退到 Python AST 解析。

用法：
    python analyze_dependencies.py --project-root <dir> [--output-dir <dir>] [--rules <file>]

输出文件（写入 --output-dir 或 .ai/evidence/deps/）：
    dependency_report.json   — 机器可读（循环依赖列表 + 边界违规列表）
    dependency_graph.mmd     — Mermaid 格式依赖图（人可读）

退出码：0 = PASS（无循环依赖和边界违规）；2 = 有 BLOCKED 项。

边界规则文件格式（rules.json）：
    {
      "layers": {
        "domain": ["src/domain/**"],
        "app": ["src/app/**"],
        "infra": ["src/infra/**"],
        "ui": ["src/ui/**"]
      },
      "allowed_deps": {
        "domain": [],
        "app": ["domain"],
        "infra": ["domain", "app"],
        "ui": ["domain", "app"]
      }
    }
"""

import argparse
import ast
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True

EXIT_PASS = 0
EXIT_BLOCK = 2


# ──────────────────────────────────────────────
# 1. 依赖提取
# ──────────────────────────────────────────────

def run_madge(project_root: Path) -> Optional[Dict[str, List[str]]]:
    """尝试使用 madge 提取 JS/TS 依赖图。不可用则返回 None。"""
    try:
        result = subprocess.run(
            ["madge", "--json", str(project_root)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root),
        )
        if result.returncode != 0:
            return None
        # madge --json 输出形如 {"a.js": ["b.js", "c.js"], ...}
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def _extract_imports_from_file(filepath: Path) -> List[str]:
    """从单个 Python 文件中提取 import 的模块名。"""
    imports = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, Exception):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _resolve_module_name(filepath: Path, project_root: Path) -> str:
    """将文件路径解析为模块名（相对于 project_root，/ → .，去掉 .py）。"""
    try:
        rel = filepath.relative_to(project_root)
    except ValueError:
        return str(filepath.stem)
    parts = list(rel.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    # 跳过 __init__
    if parts[-1] == "__init__" and len(parts) > 1:
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import_to_module(imp: str, current_module: str) -> str:
    """将 import 路径解析为内部模块名（如果 import 以项目包前缀开头）。"""
    # 如果是相对 import，尝试用当前模块上下文解析
    # 简单策略：只保留顶级包内导入
    return imp.split(".")[0]  # 取顶级包名，用于层匹配


def _analyze_python_imports(project_root: Path) -> Dict[str, List[str]]:
    """使用 AST 解析 Python 项目的 import 语句构建依赖图。"""
    deps: Dict[str, List[str]] = defaultdict(list)
    py_files = list(project_root.rglob("*.py"))

    # 排除常见虚拟环境/构建目录
    exclude_dirs = {".venv", "venv", ".tox", "__pycache__", "node_modules",
                    ".git", "build", "dist", ".eggs", ".ai"}
    for fp in py_files:
        if any(part in exclude_dirs for part in fp.parts):
            continue

        module = _resolve_module_name(fp, project_root)
        raw_imports = _extract_imports_from_file(fp)

        for imp in raw_imports:
            top = _resolve_import_to_module(imp, module)
            # 只保留项目内部模块依赖
            if top and top != module:
                deps[module].append(top)

    # 去重
    return {k: sorted(set(v)) for k, v in deps.items()}


def extract_dependency_graph(project_root: Path) -> Dict[str, List[str]]:
    """提取依赖图：优先 madge，回退到 Python AST。"""
    madge_result = run_madge(project_root)
    if madge_result is not None:
        return madge_result
    return _analyze_python_imports(project_root)


# ──────────────────────────────────────────────
# 2. 循环依赖检测（DFS）
# ──────────────────────────────────────────────

def detect_circular_deps(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    使用 DFS 检测有向图中的所有简单环。

    算法：对每个未完全访问的节点做三色 DFS：
      WHITE(0) = 未访问, GRAY(1) = 正在访问（递归栈中）, BLACK(2) = 已完成。
    当遇到 GRAY 节点时，路径中从该节点到当前节点构成一个环。
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    colors: Dict[str, int] = {node: WHITE for node in graph}
    stack: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node: str):
        colors[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in colors:
                colors[neighbor] = WHITE
            if colors[neighbor] == GRAY:
                # 找到环
                cycle_start = stack.index(neighbor)
                cycle = list(stack[cycle_start:]) + [neighbor]
                cycles.append(cycle)
            elif colors[neighbor] == WHITE:
                dfs(neighbor)
        stack.pop()
        colors[node] = BLACK

    # 收集所有图中出现的节点
    all_nodes = set(graph.keys())
    for deps in graph.values():
        all_nodes.update(deps)
    for n in all_nodes:
        if n not in colors:
            colors[n] = WHITE

    for node in list(all_nodes):
        if colors.get(node) == WHITE:
            dfs(node)

    # 去重（同一环的不同起点视为重复）
    unique = []
    seen = set()
    for cycle in cycles:
        # 规范化：将环旋转到最小元素开头
        cycle_body = cycle[:-1]  # 去掉重复的闭合节点
        min_idx = cycle_body.index(min(cycle_body))
        normalized = tuple(cycle_body[min_idx:] + cycle_body[:min_idx])
        if normalized not in seen:
            seen.add(normalized)
            unique.append(list(normalized))
    return unique


# ──────────────────────────────────────────────
# 3. 边界违规检测
# ──────────────────────────────────────────────

def load_rules(rules_path: Optional[str]) -> Dict[str, Any]:
    """加载边界规则文件。"""
    if not rules_path or not os.path.isfile(rules_path):
        return {}
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _classify_module(module_name: str, layers: Dict[str, List[str]]) -> Optional[str]:
    """根据层 glob 模式确定模块属于哪个层。"""
    for layer_name, patterns in layers.items():
        for pattern in patterns:
            if fnmatch(module_name, pattern):
                return layer_name
            # 也尝试匹配路径形式
            path_form = module_name.replace(".", "/") + ".py"
            if fnmatch(path_form, pattern):
                return layer_name
            path_form2 = module_name.replace(".", "/")
            if fnmatch(path_form2, pattern) or fnmatch(path_form2 + "/**", pattern):
                return layer_name
    return None


def detect_boundary_violations(
    graph: Dict[str, List[str]],
    rules: Dict[str, Any],
) -> List[Dict[str, str]]:
    """检测依赖边界违规。"""
    layers = rules.get("layers", {})
    allowed = rules.get("allowed_deps", {})

    if not layers or not allowed:
        return []

    violations = []

    for src_module, deps in graph.items():
        src_layer = _classify_module(src_module, layers)
        if src_layer is None:
            continue
        allowed_targets = set(allowed.get(src_layer, []))

        for dep in deps:
            tgt_layer = _classify_module(dep, layers)
            if tgt_layer is None:
                continue
            if tgt_layer == src_layer:
                continue  # 同层依赖通常允许
            if tgt_layer not in allowed_targets:
                violations.append({
                    "source": src_module,
                    "target": dep,
                    "source_layer": src_layer,
                    "target_layer": tgt_layer,
                    "reason": f"{src_layer} → {tgt_layer} 不在 allowed_deps 中",
                })

    return violations


# ──────────────────────────────────────────────
# 4. Mermaid 图生成
# ──────────────────────────────────────────────

def generate_mermaid(graph: Dict[str, List[str]],
                     cycles: List[List[str]],
                     violations: List[Dict[str, str]]) -> str:
    """生成 Mermaid 格式的依赖图。"""
    lines = ["graph LR", ""]

    # 构建违规边集合用于标记
    violation_edges = set()
    for v in violations:
        violation_edges.add((v["source"], v["target"]))

    # 构建循环边（标记为红色虚线）
    cycle_edges = set()
    for cycle in cycles:
        for i in range(len(cycle)):
            src = cycle[i]
            tgt = cycle[(i + 1) % len(cycle)]
            cycle_edges.add((src, tgt))

    # 节点
    nodes_written = set()
    for src, deps in sorted(graph.items()):
        if src not in nodes_written:
            safe_src = src.replace(".", "_").replace("/", "_").replace("-", "_")
            lines.append(f"    {safe_src}[{src}]")
            nodes_written.add(src)
        for tgt in deps:
            if tgt not in nodes_written:
                safe_tgt = tgt.replace(".", "_").replace("/", "_").replace("-", "_")
                lines.append(f"    {safe_tgt}[{tgt}]")
                nodes_written.add(tgt)
            safe_src = src.replace(".", "_").replace("/", "_").replace("-", "_")
            safe_tgt = tgt.replace(".", "_").replace("/", "_").replace("-", "_")

            edge_style = ""
            if (src, tgt) in cycle_edges:
                edge_style = ":::cycle"
            elif (src, tgt) in violation_edges:
                edge_style = ":::violation"

            lines.append(f"    {safe_src} --> {safe_tgt}{edge_style}")

    lines.append("")
    lines.append("    classDef cycle stroke:#f00,stroke-dasharray:5 5")
    lines.append("    classDef violation stroke:#f80,stroke-width:3px")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 5. 报告生成
# ──────────────────────────────────────────────

def generate_report(
    graph: Dict[str, List[str]],
    cycles: List[List[str]],
    violations: List[Dict[str, str]],
    project_root: Path,
    output_dir: Path,
) -> str:
    """生成 JSON 报告和 Mermaid 图。返回 overall 判定。"""
    has_cycles = len(cycles) > 0
    has_violations = len(violations) > 0
    overall = "PASS" if not has_cycles and not has_violations else "BLOCKED"

    # JSON report
    report = {
        "schema": "dependency_report/v1",
        "role": "system-architect",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": str(project_root.resolve()),
        "summary": {
            "total_modules": len(graph),
            "total_edges": sum(len(v) for v in graph.values()),
            "circular_deps": len(cycles),
            "boundary_violations": len(violations),
            "overall": overall,
        },
        "cycles": [{"modules": c, "length": len(c)} for c in cycles],
        "boundary_violations": violations,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dependency_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Mermaid graph
    mmd = generate_mermaid(graph, cycles, violations)
    mmd_path = output_dir / "dependency_graph.mmd"
    mmd_path.write_text(mmd, encoding="utf-8")

    return overall


# ──────────────────────────────────────────────
# 6. CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="依赖分析与循环依赖检测")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output-dir", default=None, help="报告输出目录（默认 .ai/evidence/deps/）")
    parser.add_argument("--rules", default=None, help="边界规则 JSON 文件路径")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output_dir) if args.output_dir else project_root / ".ai" / "evidence" / "deps"

    if not project_root.is_dir():
        print(json.dumps({"error": f"项目目录不存在: {project_root}"}))
        sys.exit(2)

    print(f"[analyze_dependencies] 项目: {project_root}", file=sys.stderr)
    print(f"[analyze_dependencies] 输出: {output_dir}", file=sys.stderr)

    # 提取依赖图
    graph = extract_dependency_graph(project_root)
    print(f"[analyze_dependencies] 提取到 {len(graph)} 个模块", file=sys.stderr)

    # 检测循环依赖
    cycles = detect_circular_deps(graph)
    if cycles:
        print(f"[analyze_dependencies] 发现 {len(cycles)} 个循环依赖:", file=sys.stderr)
        for c in cycles:
            print(f"  - {' → '.join(c)}", file=sys.stderr)

    # 检测边界违规
    rules = load_rules(args.rules)
    violations: List[Dict[str, str]] = []
    if rules:
        violations = detect_boundary_violations(graph, rules)
        if violations:
            print(f"[analyze_dependencies] 发现 {len(violations)} 个边界违规:", file=sys.stderr)
            for v in violations:
                print(f"  - {v['source']} → {v['target']}: {v['reason']}", file=sys.stderr)
    else:
        print("[analyze_dependencies] 未提供边界规则，跳过边界违规检测", file=sys.stderr)

    # 生成报告
    overall = generate_report(graph, cycles, violations, project_root, output_dir)

    if overall == "BLOCKED":
        print("\n[analyze_dependencies] BLOCKED — 存在架构问题", file=sys.stderr)
        if cycles:
            print(f"  循环依赖: {len(cycles)} 个", file=sys.stderr)
        if violations:
            print(f"  边界违规: {len(violations)} 个", file=sys.stderr)
        sys.exit(EXIT_BLOCK)
    else:
        print("\n[analyze_dependencies] PASS — 依赖结构健康")
        sys.exit(EXIT_PASS)


if __name__ == "__main__":
    main()
