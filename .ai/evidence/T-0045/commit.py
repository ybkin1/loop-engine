import subprocess
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = [
    "loop_core/audit_ledger.py",
    "tools/tool_certify_role.py",
    "tools/tool_governance_status.py",
    "tools/tool_state.py",
    "tools/tool_review_packet.py",
    "tools/tool_audit_log.py",
    "tools/server.py",
    ".ai/state.yaml",
]
subprocess.run(f"git add -- {' '.join(files)}", cwd=ROOT, shell=True, check=True)
msg = (
    "v3.4: MCP governance tools — audit ledger + certify + status + state + review_packet\n\n"
    "- NEW: loop_core/audit_ledger.py — chain-hashed append-only JSONL audit log\n"
    "- NEW: tool_certify_role — run role capability challenges via MCP\n"
    "- NEW: tool_governance_status — HEALTHY/DEGRADED/BLOCKED summary\n"
    "- NEW: tool_state — query project state (phase/task/gate)\n"
    "- NEW: tool_review_packet — human-readable gate approval packets\n"
    "- NEW: tool_audit_log — append/verify chain-hashed audit entries\n"
    "- server.py: registered 5 new tools (12 total)\n"
    "- 2218 passed, 0 regressions"
)
r = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)
subprocess.run("git log --oneline -3", cwd=ROOT, shell=True)
