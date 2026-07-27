import subprocess
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = ['hooks/scripts/hook_common.py', 'hooks/scripts/_hook_bash.py', 'tests/test_hook_integration.py',
         'loop_core/intent_router.py']
subprocess.run(f'git add -- {" ".join(files)}', cwd=ROOT, shell=True, check=True)
msg = 'v3.5.1: hook_common.py split — 841→689 lines, Bash extracted to _hook_bash.py\n\n- _hook_bash.py: 157 lines — shell tokenizer + write detection engine\n- hook_common.py: 689 lines — imports _hook_bash, keeps other utilities\n- Fixed sudo tokenizer bug (sudo apt-get install → correctly extracts apt-get)\n- Fixed npm --dry-run false positive\n- Fixed negation detection: "without any payment"\n- Integration tests updated to copy _hook_bash.py (4 locations)\n- test_hook_integration: 30/30 pass'
r = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)
subprocess.run('git log --oneline -3', cwd=ROOT, shell=True)
