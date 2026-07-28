# Fix remaining E701/E702 issues
import os
n = chr(10)

# repair_continuity.py — f-string lines with ; continue
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\governance\repair_continuity.py"
c = open(p, encoding="utf-8").read()

# Line 37: errors.append(f"missing: {item[chr(39)+chr(39)+chr(112)+chr(97)+chr(116)+chr(104)+chr(39)+chr(39)]}"); continue
old1 = chr(34).join([chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+chr(39)+"missing: {item[","path","]}","); continue"])
new1 = chr(34).join(["errors.append(f","missing: {item[","path","]}",")" + n + "            continue"])
c = c.replace(old1, new1)

# Line 43: errors.append(f"read error: {item[chr(39)+chr(39)+chr(112)+chr(97)+chr(116)+chr(104)+chr(39)+chr(39)]}: {e}"); continue
old2 = chr(34).join(["errors.append(f","read error: {item[","path","]}: {e}","); continue"])
new2 = chr(34).join(["errors.append(f","read error: {item[","path","]}: {e}",")" + n + "            continue"])
c = c.replace(old2, new2)

# Line 56: print("Usage: python repair_continuity.py <project_root>"); sys.exit(1)
lt = chr(60)
gt = chr(62)
old3 = chr(34).join(["print(","Usage: python repair_continuity.py ",lt,"project_root",gt,"","); sys.exit(1)"])
new3 = chr(34).join(["print(","Usage: python repair_continuity.py ",lt,"project_root",gt,"",")" + n + "        sys.exit(1)"])
c = c.replace(old3, new3)

# Line 59: print(f"ERROR: not a directory: {root}"); sys.exit(1)
old4 = chr(34).join(["print(f","ERROR: not a directory: {root}","); sys.exit(1)"])
new4 = chr(34).join(["print(f","ERROR: not a directory: {root}",")" + n + "        sys.exit(1)"])
c = c.replace(old4, new4)

open(p, "w", encoding="utf-8").write(c)
print("FIXED repair_continuity remaining")

# session_brief.py — E401 multiple imports on one line
p2 = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\hooks\session_brief.py"
c2 = open(p2, encoding="utf-8").read()
c2 = c2.replace("import json, logging, sys", "import json" + n + "import logging" + n + "import sys")
open(p2, "w", encoding="utf-8").write(c2)
print("FIXED session_brief")

print("ALL DONE")
