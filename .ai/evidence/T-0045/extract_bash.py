"""Replace Bash section in hook_common.py with import from _hook_bash."""
path = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts\hook_common.py'
lines = open(path, encoding='utf-8').readlines()

# Bash section: lines 394-552 (0-indexed 393-551)
import_block = [
    '\n',
    '# ── Bash analysis — imported from _hook_bash ──\n',
    'from _hook_bash import (\n',
    '    shell_tokenize, is_write_command, has_write_operations, is_readonly_command,\n',
    '    _WRITE_CMDS, _GIT_WRITE, _GIT_RO, _RO_CMDS,\n',
    ')\n',
    '\n',
]

new_lines = lines[:393] + import_block + lines[552:]
open(path, 'w', encoding='utf-8').write(''.join(new_lines))

print(f'hook_common.py: {len(new_lines)} lines (was {len(lines)})')
print(f'Reduction: {len(lines) - len(new_lines)} lines removed')
