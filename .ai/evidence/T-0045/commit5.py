import subprocess
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
# Add all modified tracked files (excluding __pycache__)
r = subprocess.run('git add -u -- ":!*__pycache__*"', cwd=ROOT, shell=True, capture_output=True, text=True)
# Also add new untracked files (excluding __pycache__)
r2 = subprocess.run('git add agents/test-engineer/SKILL.md', cwd=ROOT, shell=True, capture_output=True, text=True)
msg = 'v3.5.2: finalize — remaining SKILL.md updates + script enhancements + clean state'
r3 = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, shell=True, capture_output=True, text=True)
print(r3.stdout or r3.stderr)
subprocess.run('git status --short', cwd=ROOT, shell=True)
