import subprocess, sys
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = [
    "loop_core/state_machine.py",
    "loop_core/hard_constraints.py",
    "loop_core/enforcement_hub.py",
    "loop_core/role_capability.py",
    "hooks/scripts/_hook_bash.py",
    ".ai/state.yaml",
    ".ai/tasks/T-0044.md",
]
r = subprocess.run(f"git add -- {' '.join(files)}", cwd=ROOT, capture_output=True, text=True, shell=True)
if r.returncode != 0: print("ADD ERROR:", r.stderr); sys.exit(1)
msg = (
    "v3.3: Qoder learnings port + role domain separation + atomic write + initProject\n\n"
    "- atomicWrite: state.yaml writes use .tmp + rename (corruption prevention)\n"
    "- evaluateCondition: 4-type gate condition evaluation (role/evidence/phase/manual)\n"
    "- initProject: one-step project initialization with default 6-phase setup\n"
    "- C4 path aggregation: collect allowed_paths from active task definitions\n"
    "- Role domain separation: DEVELOPMENT/QUALITY/GOVERNANCE domains + cross-domain review check\n"
    "- 11 role challenges: expanded from 4 to 11 executable challenge definitions\n"
    "- _hook_bash.py: logical separation module for Bash analysis functions\n"
    "- 2218 passed, 0 regressions"
)
r2 = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, capture_output=True, text=True, shell=True)
print(r2.stdout or r2.stderr)
subprocess.run("git log --oneline -4", cwd=ROOT, shell=True)
