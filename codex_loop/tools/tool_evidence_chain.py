"""evidence_chain — Verify evidence chain integrity and freeze evidence with content hash."""
import subprocess
import sys
from pathlib import Path


def run_verify(project_root: str, strict: bool = False) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "scripts" / "evidence_chain.py"

    if not script.exists():
        # Fallback: basic chain verification from chain.yaml
        return _basic_verify(root, strict)

    cmd = [sys.executable, str(script), "--project-root", str(root), "--verify"]
    if strict:
        cmd.append("--strict")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        issues = [line.strip("- ") for line in r.stderr.splitlines() if line.startswith("  -")]
        return {"overall": "PASS" if r.returncode == 0 else "BLOCKED", "issues": issues}
    except subprocess.TimeoutExpired:
        return {"error": "evidence verify timed out", "overall": "TIMEOUT"}
    except Exception as e:
        return {"error": str(e), "overall": "ERROR"}


def run_freeze(project_root: str, file: str) -> dict:
    root = Path(project_root).resolve()
    plugin_root = Path(__file__).resolve().parent.parent
    script = plugin_root / "scripts" / "evidence_chain.py"

    if not script.exists():
        return {"success": False, "message": "evidence_chain.py not available"}

    try:
        r = subprocess.run(
            [sys.executable, str(script), "--project-root", str(root), "--freeze", "--file", file],
            capture_output=True, text=True, timeout=30,
        )
        return {"success": r.returncode == 0, "message": r.stdout.strip() or r.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "evidence freeze timed out"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _basic_verify(root: Path, strict: bool) -> dict:
    """Basic evidence chain verification from chain.yaml when evidence_chain.py is unavailable."""
    import hashlib

    chain_file = root / ".zcode" / "skills" / "loop-governance" / "chain.yaml"
    if not chain_file.exists():
        chain_file = root / "skills" / "loop-governance" / "chain.yaml"
    if not chain_file.exists():
        return {"overall": "BLOCKED", "issues": ["chain.yaml not found"]}

    try:
        import yaml
        with open(chain_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return {"overall": "BLOCKED", "issues": [f"Cannot read chain.yaml: {e}"]}

    nodes = config.get("chain", [])
    issues = []
    for node in nodes:
        node_file = root / node["file"]
        if not node_file.exists():
            if node.get("required", False) and strict:
                issues.append(f"MISSING required node: {node['name']} ({node['file']})")
            continue
        # Hash the file
        sha = hashlib.sha256(node_file.read_bytes()).hexdigest()
        issues.append(f"[ok] {node['name']}: sha256={sha[:16]}...")

    return {"overall": "BLOCKED" if issues and strict else "PASS", "issues": issues, "nodes": len(nodes)}
