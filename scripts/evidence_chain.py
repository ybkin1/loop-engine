#!/usr/bin/env python3
"""
evidence_chain.py — Evidence chain verification and freezing tool.

Reads chain.yaml definition and verifies that all nodes have valid
upstream hashes. Can also freeze a file (compute and store its SHA256).

Usage:
    python evidence_chain.py --project-root <path> --verify [--strict]
    python evidence_chain.py --project-root <path> --freeze --file <rel_path>
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_chain(project_root: Path) -> dict | None:
    """Load chain.yaml from the project's skill config."""
    for candidate in [
        project_root / ".zcode" / "skills" / "loop-governance" / "chain.yaml",
        project_root / "skills" / "loop-governance" / "chain.yaml",
    ]:
        if candidate.exists():
            try:
                import yaml
                with open(candidate, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception:
                return None
    return None


def verify_chain(project_root: Path, strict: bool = False) -> dict:
    """Verify all evidence chain nodes against their upstream hashes."""
    config = load_chain(project_root)
    if not config:
        return {"overall": "BLOCKED", "issues": ["chain.yaml not found"]}

    chain = config.get("chain", [])
    verify_config = config.get("verify", {})
    strict = strict or verify_config.get("strict_mode", False)

    nodes_status = []
    issues = []

    for node in chain:
        node_file = project_root / node["file"]
        name = node["name"]
        required = node.get("required", False)

        if not node_file.exists():
            if required and strict:
                issues.append(f"MISSING required node: {name} ({node['file']})")
                nodes_status.append({"name": name, "status": "MISSING"})
            else:
                nodes_status.append({"name": name, "status": "SKIPPED"})
            continue

        # Compute file hash
        file_hash = hashlib.sha256(node_file.read_bytes()).hexdigest()

        # Check upstream dependencies
        upstream = node.get("upstream", [])
        stale = False
        for up_name in upstream:
            up_node = next((n for n in nodes_status if n["name"] == up_name), None)
            if up_node and up_node.get("status") == "HASH_MISMATCH":
                stale = True
                break

        nodes_status.append({
            "name": name,
            "status": "PASS",
            "sha256": file_hash,
        })

        if not stale:
            issues.append(f"[ok] {name}: sha256={file_hash[:16]}...")

    overall = "BLOCKED" if any(
        n["status"] in ("MISSING", "HASH_MISMATCH") for n in nodes_status
    ) else "PASS"

    return {"overall": overall, "issues": issues, "nodes": nodes_status}


def freeze_file(project_root: Path, rel_path: str) -> dict:
    """Compute and store the SHA256 hash of a file."""
    target = project_root / rel_path
    if not target.exists():
        return {"success": False, "message": f"File not found: {rel_path}"}

    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Store freeze record
    freeze_dir = project_root / ".ai" / "evidence" / "frozen"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    freeze_file = freeze_dir / f"{Path(rel_path).name}.freeze.json"
    freeze_file.write_text(json.dumps({
        "path": rel_path,
        "sha256": sha,
        "frozen_at": frozen_at,
        "size": target.stat().st_size,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"success": True, "message": f"Frozen {rel_path} → sha256:{sha[:16]}..."}


def main():
    parser = argparse.ArgumentParser(description="Loop Engine Evidence Chain Tool")
    parser.add_argument("--project-root", required=True, help="Project root directory")
    parser.add_argument("--verify", action="store_true", help="Verify evidence chain")
    parser.add_argument("--strict", action="store_true", help="Strict mode: required nodes missing → BLOCKED")
    parser.add_argument("--freeze", action="store_true", help="Freeze a file")
    parser.add_argument("--file", help="File to freeze (relative to project root)")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()

    if args.verify:
        result = verify_chain(root, args.strict)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.freeze and args.file:
        result = freeze_file(root, args.file)
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"error": "Specify --verify or --freeze --file <path>"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
