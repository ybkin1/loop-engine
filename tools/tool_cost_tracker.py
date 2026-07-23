"""cost_report — Generate token cost report aggregated by role and phase."""
import json
import subprocess
import sys
from pathlib import Path


def run_report(project_root: str) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "scripts" / "cost_tracker.py"

    if not script.exists():
        # Fallback: return empty report, cost tracker not yet implemented
        return {"summary": {"total_tokens": 0}, "by_role": {}, "by_phase": {}, "note": "cost_tracker.py not available"}

    try:
        r = subprocess.run(
            [sys.executable, str(script), "--project-root", str(root), "--report", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.stdout.strip():
            return json.loads(r.stdout)
        report_file = root / ".ai" / "evidence" / "costs" / "cost_report.json"
        if report_file.exists():
            return json.loads(report_file.read_text(encoding="utf-8"))
        return {"summary": {"total_tokens": 0}}
    except subprocess.TimeoutExpired:
        return {"error": "cost report timed out", "summary": {"total_tokens": 0}}
    except Exception as e:
        return {"error": str(e), "summary": {"total_tokens": 0}}
