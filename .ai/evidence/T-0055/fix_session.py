p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\hooks\session_brief.py"
c = open(p, encoding="utf-8").read()
old = chr(34).join(["f","File: {(root / ",".ai"," / ","state.yaml",")}",""])
new = chr(34).join(["f","File: {(root / ",chr(39)+".ai"+chr(39)," / ",chr(39)+"state.yaml"+chr(39),")}",""])
c = c.replace(old, new)
open(p, "w", encoding="utf-8").write(c)
print("FIXED session_brief f-string")
