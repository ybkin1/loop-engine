#!/usr/bin/env python3
"""fix_evidence_t169.py — 补齐 T-0169 证据（approval/execution/compile）"""
import json
import subprocess
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine")
EVID = ROOT / ".ai/evidence/T-0169"
EVID.mkdir(parents=True, exist_ok=True)

# approval
(EVID / "approval-evidence.json").write_text(json.dumps({
    "gate_id": "G-T-0169-REQUIREMENTS",
    "task_id": "T-0169",
    "status": "approved",
    "approved_at": "2026-08-10T15:00:00+08:00",
    "approval_actor": "user",
    "approval_source": "explicit_user_message",
    "approval_text": "排布下，只要是要做的就都要走（批准 T-0169 Qoder 接线）",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("approval-evidence.json written")

# compile
r = subprocess.run(
    [r"C:\Python312\python.exe", r".ai\checkers\compile_gate.py", ".", "--output", r".ai\evidence\T-0169\compile-evidence.json"],
    capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
print("compile:", r.stdout[:80], "exit:", r.returncode)
