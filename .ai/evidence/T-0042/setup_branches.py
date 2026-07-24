import subprocess, os, shutil

total_repo = r'C:\Users\Administrator\ZCodeProject\loop-engine-total'

# ── ZCode branch ──
print("=== Creating zcode branch ===")
subprocess.run('git checkout -b zcode', cwd=total_repo, shell=True, check=True)

# Copy ZCode project files (excluding .git, __pycache__, node_modules)
zcode_src = r'C:\Users\Administrator\ZCodeProject\loop-engine'
exclude = {'.git', '__pycache__', 'node_modules', '.pytest_cache', 'venv', '.venv', 'dist', 'build'}

for item in os.listdir(zcode_src):
    if item in exclude:
        continue
    src_path = os.path.join(zcode_src, item)
    dst_path = os.path.join(total_repo, item)
    if os.path.isdir(src_path):
        shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
    else:
        shutil.copy2(src_path, dst_path)

# Commit zcode
subprocess.run('git add -A', cwd=total_repo, shell=True, check=True)
subprocess.run('git commit -m "zcode: ZCode adapter — Python hook system + 11 role agents + shell tokenizer"', cwd=total_repo, shell=True, check=True)
print("ZCode branch created")

# ── Qoder branch ──
print("=== Creating qoder branch ===")
subprocess.run('git checkout main', cwd=total_repo, shell=True, check=True)
subprocess.run('git checkout -b qoder', cwd=total_repo, shell=True, check=True)

# Copy Qoder project files
qoder_src = r'C:\Users\Administrator\.qoder-cn\loop-engine-lab'
for item in os.listdir(qoder_src):
    if item in exclude:
        continue
    src_path = os.path.join(qoder_src, item)
    dst_path = os.path.join(total_repo, item)
    try:
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache', 'node_modules'))
        else:
            shutil.copy2(src_path, dst_path)
    except Exception as e:
        print(f"  Skip {item}: {e}")

# Commit qoder
subprocess.run('git add -A', cwd=total_repo, shell=True, check=True)
subprocess.run('git commit -m "qoder: Qoder adapter — TypeScript MCP protocol + role engine + certification"', cwd=total_repo, shell=True, check=True)
print("Qoder branch created")

# ── Back to main ──
subprocess.run('git checkout main', cwd=total_repo, shell=True, check=True)
print("\n=== Branches ===")
subprocess.run('git branch', cwd=total_repo, shell=True)
