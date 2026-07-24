"""dependency_analysis — Analyze module dependency graph, detect cycles and boundary violations."""
import json
import subprocess
import sys
from pathlib import Path


def run(project_root: str, rules_file: str = None) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "agents" / "system-architect" / "scripts" / "analyze_dependencies.py"

    if not script.exists():
        return {"error": f"dependency analysis script not found: {script}", "overall": "UNAVAILABLE"}

    cmd = [sys.executable, str(script), "--project-root", str(root)]
    if rules_file:
        cmd += ["--rules", rules_file]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        report_file = root / ".ai" / "evidence" / "deps" / "dependency_report.json"
        if report_file.exists():
            return json.loads(report_file.read_text(encoding="utf-8"))
        if r.stdout.strip():
            return json.loads(r.stdout)
        return {"overall": "BLOCKED" if r.returncode != 0 else "PASS", "stderr": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"error": "dependency analysis timed out after 60s", "overall": "TIMEOUT"}
    except Exception as e:
        return {"error": str(e), "overall": "ERROR"}
