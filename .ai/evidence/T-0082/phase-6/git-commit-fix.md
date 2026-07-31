# T-0082: Git Commit Ordering Fix

- **issue**: DISPATCH_REQUIRED blocked git add/commit before git exemption
- **fix**: git commit/status ops exempted from DISPATCH_REQUIRED gate (loop_enforcement.py)
- **verification**: py_compile OK, test_enforcement.py 27 passed, git status works: ALLOWED (rc=0, no BLOCKED message)

## Details

- **File**: `hooks/scripts/loop_enforcement.py` (DISPATCH_REQUIRED gate, ~line 874)
- **Change**: added `_git_commit_exempt` check (git add/commit/diff/status/log/branch/show/tag/config) to the DISPATCH_REQUIRED condition; existing git exemption block at ~line 963 left untouched.
- **Gate still enforced**: non-git business ops (`ls src/`, `Write src/new_file.py`) still return EXIT_BLOCK (rc=2) with "SETUP_INCOMPLETE: runtime projection missing; DISPATCH_REQUIRED for active task T-0082".
- **Simulation**: hook stdin with active task T-0082 + missing runtime projection:
  - `git status --short | head -5` → EXIT_PASS (rc=0)
  - `ls src/` → EXIT_BLOCK (rc=2)
