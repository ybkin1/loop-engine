"""contract_validate — Validate interface contract JSON schema, optionally check against actual code."""
import json
import subprocess
import sys
from pathlib import Path


def run(project_root: str, contract_file: str, check_actual: bool = False) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "agents" / "module-architect" / "scripts" / "validate_contract.py"

    if not script.exists():
        return {"error": f"contract validation script not found: {script}", "valid": False}

    cmd = [sys.executable, str(script), "--contract", contract_file]
    if check_actual:
        cmd += ["--check-actual", "--project-root", str(root)]
    else:
        cmd += ["--check-schema-only"]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.stdout.strip():
            return json.loads(r.stdout)
        return {"valid": r.returncode == 0, "errors": [], "warnings": []}
    except subprocess.TimeoutExpired:
        return {"error": "contract validation timed out", "valid": False}
    except Exception as e:
        return {"error": str(e), "valid": False}
