p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\hooks\session_brief.py"
c = open(p, encoding="utf-8").read()
# Fix the f-string quote reuse
old = chr(34).join(["f","File: {(root / ",chr(34)+".ai"+chr(34)," / ",chr(34)+"state.yaml"+chr(34),")}",""])
new = chr(34).join(["f","File: {(root / ",chr(39)+".ai"+chr(39)," / ",chr(39)+"state.yaml"+chr(39),")}",""])
print("OLD:", repr(old)[:80])
print("NEW:", repr(new)[:80])
if old in c:
    c = c.replace(old, new)
    open(p, "w", encoding="utf-8").write(c)
    print("FIXED")
else:
    print("NOT FOUND — skipping")
