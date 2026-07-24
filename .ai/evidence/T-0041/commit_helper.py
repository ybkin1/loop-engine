#!/usr/bin/env python3
"""Git commit helper for loop-engine delivery."""
import subprocess
import sys

ROOT = r"C:\Users\Administrator\ZCodeProject\loop-engine"

def run(cmd):
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout)
    return result.returncode

files = [
    "loop_core/enforcement_hub.py",
    "tests/test_enforcement_hub.py",
    "hooks/scripts/role_isolation.py",
    "agents/main-thread/CONTRACT.yaml",
    "demo/loop-demo-todo/",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/gates.yaml",
    ".ai/HANDOFF.md",
    ".ai/tasks/T-0040.md",
    ".ai/tasks/T-0041.md",
    ".ai/evidence/T-0040/",
    ".ai/evidence/T-0041/",
]

# Stage
ret = run(f"git add -- {' '.join(files)}")
if ret != 0:
    sys.exit(ret)

# Commit
msg = (
    "v3.0.0: T-0040 EnforcementHub + T-0041 vertical slice (loop-demo-todo CLI)\n\n"
    "T-0040: Eliminate model self-discipline reliance\n"
    "- enforcement_hub.py: Hook<->Core governance bridge\n"
    "- role_isolation.py v2.0: HARD self-review blocking\n"
    "- 39 new tests, 2116 regression tests pass\n\n"
    "T-0041: External vertical slice validation\n"
    "- loop-demo-todo CLI: S1-S6 complete Loop\n"
    "- 23 tests, user-observable result verified"
)
ret = run(f'git commit -m "{msg}"')
sys.exit(ret)
