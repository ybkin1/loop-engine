"""Split hook_common.py: extract Bash tokenizer + detection into _hook_bash.py."""
import re

base = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts'
common_path = rf'{base}\hook_common.py'
bash_path = rf'{base}\_hook_bash.py'

content = open(common_path, encoding='utf-8').read()
lines = content.splitlines()

# Find section boundaries
shell_start = None
bash_end = None
for i, line in enumerate(lines):
    if '# ── Shell Tokenizer' in line:
        shell_start = i
    if shell_start and i > shell_start + 300 and line.startswith('# ──') and 'Shell Tokenizer' not in line and 'Write Command' not in line and 'Bash' not in line:
        if bash_end is None:
            bash_end = i - 1
            break

# Shell tokenizer section is from shell_start to just before the next # ── section
# Let me find the exact end of the Bash-related code
for i, line in enumerate(lines):
    if i > 400 and line.startswith('# ──') and 'Bash' not in line and 'Token' not in line and 'Write' not in line:
        if bash_end is None:
            bash_end = i
            break

print(f"Shell tokenizer starts at line {shell_start + 1}")
print(f"Bash section ends at line {bash_end}")

# Extract Bash section
bash_lines = lines[shell_start:bash_end]
bash_content = '\n'.join([
    '"""Bash command analysis — shell tokenizer, write detection, readonly classification. v3.1"""',
    'from __future__ import annotations',
    'import re',
    '',
]) + '\n' + '\n'.join(bash_lines)

# Write _hook_bash.py
open(bash_path, 'w', encoding='utf-8').write(bash_content)

# Update hook_common.py: remove Bash section, add import
new_lines = lines[:shell_start] + [
    '',
    '# ── Bash analysis imported from _hook_bash ──',
    'from _hook_bash import (',
    '    shell_tokenize, is_write_command, has_write_operations, is_readonly_command,',
    '    _WRITE_CMDS, _GIT_WRITE, _GIT_RO, _RO_CMDS, _extract_git_subcommand,',
    ')',
    '',
] + lines[bash_end:]

open(common_path, 'w', encoding='utf-8').write('\n'.join(new_lines))

# Stats
bash_lc = len(bash_lines)
common_lc = len(new_lines)
print(f"_hook_bash.py: {bash_lc} lines")
print(f"hook_common.py: {common_lc} lines (was {len(lines)})")
print(f"Reduction: {len(lines) - common_lc} lines extracted")
