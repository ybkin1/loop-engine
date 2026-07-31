"""quality_gates_run — Run quality gates (lint/typecheck/test/coverage/audit/build).

DEPRECATED: This is a thin subprocess wrapper around
agents/quality-engineer/scripts/run_quality_gates.py. For in-process analysis,
use loop_core.static_analyzer.analyze_project() directly.
This wrapper maintained for backward compatibility only.
"""
import json
import subprocess
import sys
from pathlib import Path


def run(project_root: str, output_dir: str = None) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "agents" / "quality-engineer" / "scripts" / "run_quality_gates.py"

    if not script.exists():
        return {"error": f"quality gates script not found: {script}", "overall": "UNAVAILABLE"}

    cmd = [sys.executable, str(script), "--project-root", str(root), "--json"]
    if output_dir:
        cmd += ["--output-dir", output_dir]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.stdout.strip():
            return json.loads(r.stdout)
        return {"overall": "UNKNOWN", "exit_code": r.returncode, "stderr": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"error": "quality gates timed out after 180s", "overall": "TIMEOUT"}
    except Exception as e:
        return {"error": str(e), "overall": "ERROR"}
