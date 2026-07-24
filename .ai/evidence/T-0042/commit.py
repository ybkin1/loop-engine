import subprocess, sys
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'

files = [
    "hooks/scripts/hook_common.py",
    "loop_core/intent_router.py",
    "loop_core/state_machine.py",
    "loop_core/executor.py",
    "tests/test_deep_qa_probe.py",
    "tests/test_bypass_matrix.py",
    "tests/test_enforcement_hub.py",
    "loop_engine/adapters/zcode_adapter.py",
    "loop_core/hard_constraints.py",
    "loop_core/enforcement_hub.py",
    "README.md",
    "docs/06-delivery.md",
    "pyproject.toml",
    ".ai/state.yaml",
    ".ai/task_graph.yaml",
    ".ai/gates.yaml",
    ".ai/HANDOFF.md",
    ".ai/tasks/T-0040.md",
    ".ai/tasks/T-0041.md",
    ".ai/tasks/T-0042.md",
    "agents/main-thread/CONTRACT.yaml",
    "demo/",
]

r = subprocess.run(f"git add -- {' '.join(files)}", cwd=ROOT, capture_output=True, text=True, shell=True)
if r.returncode != 0:
    print("ADD ERROR:", r.stderr)
    sys.exit(1)

msg = (
    "v3.1.0: shell tokenizer (方案B) + change iteration + Bash enhancement + deep QA\n\n"
    "- Shell tokenizer: quote/escape-aware command extraction, eliminates \\binstall\\b false positives\n"
    "- ChangeType detection: 6 change types with Chinese+English keyword support\n"
    "- Reentry validation: ProjectStatus (draft/released), REENTRY_TRANSITIONS, validate_reentry()\n"
    "- Bash enhancement: curl/wget/tar/pip/npm/rsync/scp/openssl detection via tokenizer\n"
    "- Deep QA: 75 new probe tests, 5 issues found and fixed\n"
    "- ENFORCEMENT_LEVEL: zcode_adapter MEDIUM→STRONG\n"
    "- Docs: README updated (v3.0, 2116 tests), pyproject.toml created, delivery doc synced\n"
    "- 2185 tests pass, hook_common.py 998→830 lines"
)

r2 = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, capture_output=True, text=True, shell=True)
if r2.returncode != 0:
    print("COMMIT ERROR:", r2.stderr)
else:
    print(r2.stdout)
    r3 = subprocess.run("git log --oneline -3", cwd=ROOT, capture_output=True, text=True, shell=True)
    print(r3.stdout)
