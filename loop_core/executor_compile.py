"""executor_compile.py — PhaseExecutor 编译门检查外部模块（T-0124 拆分）。

从 loop_core/executor.py 拆出：`_run_compile_gate_check` 方法体承载于此
（作为带 runner 参数的函数），壳文件方法改为调用。行为逐字节等价。
"""
from __future__ import annotations

import json as _json
import subprocess
import sys
import warnings
from pathlib import Path

from loop_core.constants import FAILED_STDERR_MAX_CHARS, truncate_with_marker


def executor_compile_check(project_root: Path, subprocess_runner: callable) -> bool:
    """Run the CompileGate checker on the project's core directories.

    Returns True if all .py files compile successfully, False otherwise.
    The compile gate is a QUALITY gate — it blocks phase advance only,
    never file writes. Evidence is stored in .ai/evidence/compile/.

    T-0124: 原 PhaseExecutor._run_compile_gate_check 方法体（self._subprocess_runner
    参数化）；调用方保持方法签名（docstring 语义不变）。
    """
    checker_script = project_root / ".ai" / "checkers" / "compile_gate.py"
    if not checker_script.exists():
        # Compile gate checker not available — warn but don't block
        warnings.warn(
            "COMPILE_GATE_UNAVAILABLE: .ai/checkers/compile_gate.py not found. "
            "Compile check skipped — phase advance allowed."
        )
        return True

    try:
        result = subprocess_runner(
            [sys.executable, str(checker_script), str(project_root),
             "--paths", "loop_core,hooks/scripts,tests"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )

        # Parse the JSON output
        stdout = result.stdout.strip()
        if stdout:
            try:
                data = _json.loads(stdout)
                exit_code = data.get("exit_code", result.returncode)
                compiled_files = data.get("compiled_files", 0)
                total_files = data.get("total_files", 0)
                errors = data.get("errors", [])

                # Write compile evidence to .ai/evidence/compile/
                evidence_dir = project_root / ".ai" / "evidence" / "compile"
                evidence_dir.mkdir(parents=True, exist_ok=True)
                evidence_path = evidence_dir / "compile_report.json"
                evidence_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2),
                                        encoding="utf-8")

                if exit_code == 0 and not errors:
                    return True
                else:
                    import logging
                    logging.warning(
                        f"COMPILE_FAILED: {len(errors)}/{total_files} files failed to compile. "
                        f"See {evidence_path} for details."
                    )
                    return False
            except _json.JSONDecodeError:
                pass

        # Fallback: use returncode
        if result.returncode == 0:
            return True
        else:
            import logging
            logging.warning(
                f"COMPILE_FAILED: exit code {result.returncode}. "
                f"stderr: {truncate_with_marker(result.stderr, FAILED_STDERR_MAX_CHARS)}"
            )
            return False

    except subprocess.TimeoutExpired:
        import logging
        logging.warning("COMPILE_GATE_TIMEOUT: Compile check timed out after 120s.")
        return False
    except Exception as e:
        import logging
        logging.warning(f"COMPILE_GATE_ERROR: {e}")
        return False
