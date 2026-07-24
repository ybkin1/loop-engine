"""Replace old has_write_operations and is_readonly_command with tokenizer-based versions."""
path = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts\hook_common.py'
content = open(path, encoding='utf-8').read()
lines = content.splitlines()

# Find the old function locations
hw_start = None
hw_end = None
ro_start = None
ro_end = None

for i, line in enumerate(lines):
    if line.startswith('def has_write_operations(') and i > 600:
        hw_start = i
    if line.startswith('def is_readonly_command(') and i > 600:
        if hw_end is None:
            hw_end = i
        ro_start = i

# Find end of is_readonly_command
if ro_start:
    for j in range(ro_start + 1, len(lines)):
        if lines[j].startswith('def ') or lines[j].startswith('# ──'):
            ro_end = j
            break

print(f"Old has_write_operations: lines {hw_start+1}-{hw_end}")
print(f"Old is_readonly_command: lines {ro_start+1}-{ro_end}")

# Remove old functions, keep everything else
if hw_start and ro_end:
    new_lines = lines[:hw_start] + lines[ro_end:]
    open(path, 'w', encoding='utf-8').write('\n'.join(new_lines) + '\n')
    print("Removed old functions. New file has", len(new_lines), "lines")
else:
    print("Could not find functions")
