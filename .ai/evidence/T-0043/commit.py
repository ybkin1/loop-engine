import subprocess, sys
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = [
    "loop_core/intent_router.py",
    "loop_core/role_capability.py",
    "tests/test_role_capability.py",
    "tests/test_deep_qa_probe.py",
    ".ai/state.yaml",
    ".ai/tasks/T-0043.md",
]

r = subprocess.run(f"git add -- {' '.join(files)}", cwd=ROOT, capture_output=True, text=True, shell=True)
if r.returncode != 0:
    print("ADD ERROR:", r.stderr); sys.exit(1)

msg = (
    "v3.2: role capability certification + negation detection + state persistence\n\n"
    "- FIX-1: Negation detection in intent_router — \"remove the database\" no longer triggers has_database\n"
    "- FIX-3: Role capability state persistence — degradation counters survive restarts via .ai/certifications/\n"
    "- NEW: role_capability.py — 8-state certification lifecycle, 6 degradation rules, 4 role challenges\n"
    "- Persistence: save_profile/load_profile/save_all_profiles/load_all_profiles\n"
    "- 28 new tests (23 role_capability + 5 negation detection)\n"
    "- 2218 passed, 0 regressions\n"
    "- hook_common.py split deferred — integration test compatibility needs separate task"
)
r2 = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, capture_output=True, text=True, shell=True)
if r2.returncode != 0:
    print("COMMIT ERROR:", r2.stderr)
else:
    print(r2.stdout)
    r3 = subprocess.run("git log --oneline -3", cwd=ROOT, capture_output=True, text=True, shell=True)
    print(r3.stdout)
