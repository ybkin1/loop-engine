#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CompileGate — 编译门禁检查器。

纯确定性代码，不依赖 LLM。验证指定目录下的所有 .py 文件是否可成功编译。
被质量门禁系统或 enforcement hub 通过 Bash/subprocess 调用。

用法：
    python .ai/checkers/compile_gate.py <project_root> --paths "loop_core,hooks/scripts"
    python .ai/checkers/compile_gate.py . --paths "loop_core" --output compile_result.json

输出（JSON，stdout）：
    {
      "status": "pass" | "fail",
      "exit_code": 0,
      "compiled_files": 120,
      "errors": [...],
      "timestamp": "2026-07-24T..."
    }

退出码：
    0 = 全部编译通过
    1 = 有编译失败的文件
    2 = 参数错误或无法访问目录
"""

import argparse
import json
import os
import py_compile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2


def collect_python_files(project_root: Path, path_list: list[str]) -> list[Path]:
    """Collect all .py files under the specified directories (relative to project_root)."""
    files: list[Path] = []
    seen: set[str] = set()

    for rel_path in path_list:
        rel_path = rel_path.strip()
        if not rel_path:
            continue

        full_path = (project_root / rel_path).resolve()
        try:
            full_path = full_path.resolve(strict=False)
        except Exception:
            continue

        if not full_path.exists():
            continue

        if full_path.is_file() and full_path.suffix == ".py":
            abs_str = str(full_path)
            if abs_str not in seen:
                seen.add(abs_str)
                files.append(full_path)
        elif full_path.is_dir():
            for py_file in full_path.rglob("*.py"):
                # Skip __pycache__, .git, .venv, etc.
                parts = py_file.parts
                if any(p.startswith("__pycache__") or p.startswith(".git") or
                       p.startswith(".venv") or p == "venv" or
                       p.startswith("node_modules") or p.startswith("dist") or
                       p.startswith("build") for p in parts):
                    continue
                abs_str = str(py_file)
                if abs_str not in seen:
                    seen.add(abs_str)
                    files.append(py_file)

    return sorted(files)


def compile_file(file_path: Path) -> tuple[bool, str]:
    """Attempt to compile a single .py file. Returns (success, error_message)."""
    try:
        # py_compile.compile validates syntax by compiling to bytecode
        # Use dfile to set the displayed filename in error messages
        py_compile.compile(str(file_path), dfile=str(file_path), doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_compile_check(project_root: Path, path_list: list[str]) -> dict:
    """Run compilation check on all .py files under the given paths.

    Returns a dict with status, exit_code, compiled_files, errors, timestamp.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []
    compiled_count = 0
    failed_count = 0

    # Resolve project_root to absolute
    project_root = project_root.resolve()

    if not project_root.is_dir():
        return {
            "status": "fail",
            "exit_code": 2,
            "compiled_files": 0,
            "errors": [f"Project root not found: {project_root}"],
            "timestamp": timestamp,
        }

    files = collect_python_files(project_root, path_list)

    if not files:
        return {
            "status": "fail",
            "exit_code": 2,
            "compiled_files": 0,
            "errors": [f"No .py files found in paths: {path_list}"],
            "timestamp": timestamp,
        }

    for fp in files:
        ok, err = compile_file(fp)
        if ok:
            compiled_count += 1
        else:
            failed_count += 1
            errors.append({
                "file": str(fp.resolve()),
                "relative": str(fp.relative_to(project_root)) if fp.is_relative_to(project_root) else str(fp),
                "error": err,
            })

    total = compiled_count + failed_count
    # If we have files but none compiled successfully, or there are errors, mark as fail
    if total == 0:
        status = "fail"
        exit_code = 2
    elif failed_count == 0:
        status = "pass"
        exit_code = 0
    else:
        status = "fail"
        exit_code = 1

    return {
        "status": status,
        "exit_code": exit_code,
        "compiled_files": compiled_count,
        "total_files": total,
        "failed_count": failed_count,
        "errors": errors,
        "timestamp": timestamp,
    }


def main():
    parser = argparse.ArgumentParser(
        description="CompileGate — 编译门禁：验证指定目录下所有 .py 文件是否可成功编译"
    )
    parser.add_argument(
        "project_root",
        help="项目根目录路径",
    )
    parser.add_argument(
        "--paths",
        default="loop_core",
        help="逗号分隔的要检查的目录列表（相对于 project_root），默认: loop_core",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="结果输出 JSON 文件路径（可选）。也始终输出到 stdout。",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)
    path_list = [p.strip() for p in args.paths.split(",") if p.strip()]

    result = run_compile_check(project_root, path_list)

    # Always output to stdout as JSON
    json_output = json.dumps(result, ensure_ascii=False, indent=2)
    print(json_output)

    # Optionally write to file
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")

    # Exit with the computed exit code
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
