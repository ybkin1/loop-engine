import subprocess, os, shutil

total_repo = r'C:\Users\Administrator\ZCodeProject\loop-engine-total'
exclude = {'.git', '__pycache__', 'node_modules', '.pytest_cache', 'venv', '.venv', 'dist', 'build'}

def clean_worktree():
    """Remove all files except .git before copying branch code."""
    for item in os.listdir(total_repo):
        if item == '.git':
            continue
        path = os.path.join(total_repo, item)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as e:
            print(f"  Warn: can't remove {item}: {e}")

def copy_project(src_root):
    """Copy project files, skipping excluded dirs."""
    for item in os.listdir(src_root):
        if item in exclude:
            continue
        src = os.path.join(src_root, item)
        dst = os.path.join(total_repo, item)
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache', 'node_modules', '.git'))
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(f"  Skip {item}: {e}")

# ── ZCode branch ──
print("=== ZCode branch ===")
subprocess.run('git checkout zcode', cwd=total_repo, shell=True, check=True)
clean_worktree()
copy_project(r'C:\Users\Administrator\ZCodeProject\loop-engine')
subprocess.run('git add -A', cwd=total_repo, shell=True, check=True)
r = subprocess.run('git commit -m "zcode: ZCode adapter — Python hook system + 11 role agents + shell tokenizer"', cwd=total_repo, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)

# ── Qoder branch ──
print("=== Qoder branch ===")
subprocess.run('git checkout -b qoder', cwd=total_repo, shell=True, check=True)
clean_worktree()
copy_project(r'C:\Users\Administrator\.qoder-cn\loop-engine-lab')
subprocess.run('git add -A', cwd=total_repo, shell=True, check=True)
r = subprocess.run('git commit -m "qoder: Qoder adapter — TypeScript MCP protocol + role engine + certification"', cwd=total_repo, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)

# ── Back to main ──
subprocess.run('git checkout main', cwd=total_repo, shell=True, check=True)
print("\n=== Done ===")
subprocess.run('git branch -v', cwd=total_repo, shell=True)
