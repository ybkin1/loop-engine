import subprocess
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = ['hooks/scripts/_hook_bash.py', 'tests/test_bypass_matrix.py', 'tests/deep_probe_v35.py']
subprocess.run(f'git add -- {" ".join(files)}', cwd=ROOT, shell=True, check=True)
msg = 'v3.5.2: git tokenizer context-aware — stash/branch/tag subcommand handling\n\n- stash: list/show = readonly, push/pop/apply = write\n- branch/tag: listing without -d/-D = readonly, with -d/-D = write\n- Unknown git subcommands → conservative (assume write)\n- 2030 passed, 0 failures — all 7 pre-existing tokenizer tests now pass'
r = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)
subprocess.run('git log --oneline -4', cwd=ROOT, shell=True)
