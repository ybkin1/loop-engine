"""security_scan_run — Run security scan (CVE/secrets/injection/permissions)."""
import json
import subprocess
import sys
from pathlib import Path


def run(project_root: str, output_dir: str = None) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "agents" / "security-engineer" / "scripts" / "run_security_scan.py"

    if not script.exists():
        return {"error": f"security scan script not found: {script}", "overall": "UNAVAILABLE"}

    cmd = [sys.executable, str(script), "--project-root", str(root), "--json"]
    if output_dir:
        cmd += ["--output-dir", output_dir]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.stdout.strip():
            return json.loads(r.stdout)
        return {"overall": "UNKNOWN", "exit_code": r.returncode, "stderr": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"error": "security scan timed out after 180s", "overall": "TIMEOUT"}
    except Exception as e:
        return {"error": str(e), "overall": "ERROR"}
