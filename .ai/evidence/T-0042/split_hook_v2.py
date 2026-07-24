"""Split hook_common.py v2: exact boundaries."""
base = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts'
common_path = rf'{base}\hook_common.py'
bash_path = rf'{base}\_hook_bash.py'

content = open(common_path, encoding='utf-8').read()
lines = content.splitlines()

# Find boundaries
shell_start = bash_end = None
for i, line in enumerate(lines):
    if '# ── Shell Tokenizer' in line:
        shell_start = i - 1  # Include the blank line before
    if i > 400 and 'def load_tasks_for_context' in line:
        bash_end = i - 1
        break

print(f"Bash section: lines {shell_start+1} to {bash_end+1} ({bash_end - shell_start + 1} lines)")

# Extract Bash section
bash_lines = lines[shell_start:bash_end + 1]
header = '"""Bash command analysis — shell tokenizer, write detection, readonly classification. v3.1"""\nfrom __future__ import annotations\nimport re\n\n'
bash_content = header + '\n'.join(bash_lines)

open(bash_path, 'w', encoding='utf-8').write(bash_content)

# Update hook_common.py: replace Bash section with import
import_block = [
    '# ── Bash analysis imported from _hook_bash ──',
    'from _hook_bash import (',
    '    shell_tokenize, is_write_command, has_write_operations, is_readonly_command,',
    '    _WRITE_CMDS, _GIT_WRITE, _GIT_RO, _RO_CMDS, _extract_git_subcommand,',
    ')',
    '',
]

new_lines = lines[:shell_start] + import_block + lines[bash_end + 1:]
open(common_path, 'w', encoding='utf-8').write('\n'.join(new_lines))

print(f"_hook_bash.py: {len(bash_lines)+4} lines")
print(f"hook_common.py: {len(new_lines)} lines (was {len(lines)})")
