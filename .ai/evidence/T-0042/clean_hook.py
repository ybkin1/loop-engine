"""Generate clean hook_common.py — keep the first occurrence of each section, remove duplicates."""
path = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts\hook_common.py'
content = open(path, encoding='utf-8').read()

# Find the end of our new tokenizer section (after is_readonly_command)
# Everything from '# ── Shell Tokenizer' to the end of is_readonly_command is new
# Everything after that is old code we want to keep (auto_sync, HardConstraints helpers)

# Strategy: keep lines up to and including the second '# ──' marker after our new code
lines = content.splitlines()
keep_lines = []
seen_bash_section = 0
in_new_code = False

for i, line in enumerate(lines):
    if '# ── Shell Tokenizer' in line:
        in_new_code = True
    if in_new_code and line.strip().startswith('# ──') and 'Shell Tokenizer' not in line:
        seen_bash_section += 1
    if seen_bash_section >= 2:
        # Skip old duplicated sections until we hit auto_sync or HardConstraints
        if 'auto_sync_to_plugin_cache' in line or 'load_tasks_for_context' in line or 'try_import_hard_constraints' in line or '# ═══════════' in line:
            seen_bash_section = 0  # Resume keeping
    if seen_bash_section < 2:
        keep_lines.append(line)

# Write
open(path, 'w', encoding='utf-8').write('\n'.join(keep_lines) + '\n')
print(f"Cleaned: {len(keep_lines)} lines (was {len(lines)})")

# Verify functions exist
content2 = open(path, encoding='utf-8').read()
for func in ['shell_tokenize', 'is_write_command', 'has_write_operations', 'is_readonly_command',
             'auto_sync_to_plugin_cache', 'load_tasks_for_context', 'extract_target_path']:
    count = content2.count(f'def {func}')
    print(f"  {func}: {count} occurrences")
