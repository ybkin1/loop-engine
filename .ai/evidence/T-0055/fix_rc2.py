import os
n = chr(10)
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\governance\repair_continuity.py"
with open(p, encoding="utf-8") as f:
    lines = f.readlines()
fixed = 0
for i, line in enumerate(lines):
    s = line.rstrip()
    if s.endswith(": continue") and "not in item" in s:
        indent = len(s) - len(s.lstrip())
        lines[i] = " " * indent + s.lstrip()[:s.rindex(":")] + ":" + n + " " * (indent + 4) + "continue" + n
        fixed += 1
    elif "item[\"sha256\"] = ah; item[\"size\"] = sz; fixed += 1" in s:
        indent = len(s) - len(s.lstrip())
        lines[i] = " " * indent + "item[\"sha256\"] = ah" + n + " " * (indent + 4) + "item[\"size\"] = sz" + n + " " * (indent + 4) + "fixed += 1" + n
        fixed += 1
    elif "print(\"Usage: python repair_continuity.py" in s and s.rstrip().endswith("sys.exit(1)"):
        indent = len(s) - len(s.lstrip())
        idx = s.index("\")")
        lines[i] = s[:idx+2] + n + " " * (indent + 4) + "sys.exit(1)" + n
        fixed += 1
    elif "print(f\"ERROR: not a directory:" in s and s.rstrip().endswith("sys.exit(1)"):
        indent = len(s) - len(s.lstrip())
        idx = s.index("\")")
        lines[i] = s[:idx+2] + n + " " * (indent + 4) + "sys.exit(1)" + n
        fixed += 1
with open(p, "w", encoding="utf-8") as f:
    f.writelines(lines)
print(f"FIXED {fixed} lines")
