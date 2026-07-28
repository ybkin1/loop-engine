p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\hooks\session_brief.py"
with open(p, encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "File: {(root /" in line and "state.yaml" in line:
        lines[i] = "        f\"File: {(root / " + chr(39) + ".ai" + chr(39) + " / " + chr(39) + "state.yaml" + chr(39) + ")}\"," + chr(10)
        break
with open(p, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("FIXED")
