
import os

# Fix #1: enforcement_hub.py check_cross_domain_review — split inline statements
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\core\enforcement_hub.py"
with open(p, "r", encoding="utf-8") as f: c = f.read()

old = """        dev_domains = []
        if developer_role in cls.DEVELOPMENT_ROLES: dev_domains.append("development")
        if developer_role in cls.QUALITY_ROLES: dev_domains.append("quality")
        if developer_role in cls.GOVERNANCE_ROLES: dev_domains.append("governance")

        rev_domains = []
        if reviewer_role in cls.DEVELOPMENT_ROLES: rev_domains.append("development")
        if reviewer_role in cls.QUALITY_ROLES: rev_domains.append("quality")
        if reviewer_role in cls.GOVERNANCE_ROLES: rev_domains.append("governance")"""

new = """        dev_domains = []
        if developer_role in cls.DEVELOPMENT_ROLES:
            dev_domains.append("development")
        if developer_role in cls.QUALITY_ROLES:
            dev_domains.append("quality")
        if developer_role in cls.GOVERNANCE_ROLES:
            dev_domains.append("governance")

        rev_domains = []
        if reviewer_role in cls.DEVELOPMENT_ROLES:
            rev_domains.append("development")
        if reviewer_role in cls.QUALITY_ROLES:
            rev_domains.append("quality")
        if reviewer_role in cls.GOVERNANCE_ROLES:
            rev_domains.append("governance")"""

c = c.replace(old, new)
with open(p, "w", encoding="utf-8") as f: f.write(c)
print("FIX1: enforcement_hub.py")

# Fix #2: repair_continuity.py — split inline/semicolons
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\governance\repair_continuity.py"
with open(p, "r", encoding="utf-8") as f: c = f.read()

c = c.replace(
    "        if not isinstance(item, dict) or \"path\" not in item: continue",
    "        if not isinstance(item, dict) or \"path\" not in item:
            continue"
)
c = c.replace(
    '            errors.append(f"missing: {item[\'path\']}"); continue',
    '            errors.append(f"missing: {item[\'path\']}")
            continue'
)
c = c.replace(
    '            errors.append(f"read error: {item[\'path\']}: {e}"); continue',
    '            errors.append(f"read error: {item[\'path\']}: {e}")
            continue'
)
c = c.replace(
    '            item["sha256"] = ah; item["size"] = sz; fixed += 1',
    '            item["sha256"] = ah
            item["size"] = sz
            fixed += 1'
)
c = c.replace(
    '        print("Usage: python repair_continuity.py <project_root>"); sys.exit(1)',
    '        print("Usage: python repair_continuity.py <project_root>")
        sys.exit(1)'
)
c = c.replace(
    '        print(f"ERROR: not a directory: {root}"); sys.exit(1)',
    '        print(f"ERROR: not a directory: {root}")
        sys.exit(1)'
)
with open(p, "w", encoding="utf-8") as f: f.write(c)
print("FIX2: repair_continuity.py")

# Fix #3: sync_plugin_cache.py — split inline/semicolons
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\governance\sync_plugin_cache.py"
with open(p, "r", encoding="utf-8") as f: c = f.read()

c = c.replace("    if not local.is_dir(): return 0", "    if not local.is_dir():
        return 0")
c = c.replace("        if f.name.startswith(\"__\"): continue", "        if f.name.startswith(\"__\"):
            continue")
c = c.replace("            shutil.copy2(str(f), str(t)); n += 1", "            shutil.copy2(str(f), str(t))
            n += 1")
c = c.replace("    if n: print(f\"[sync] {n} hook scripts synced.\")", "    if n:
        print(f\"[sync] {n} hook scripts synced.\")")
c = c.replace("    if not local.is_dir(): return 0", "    if not local.is_dir():
        return 0")
c = c.replace("            shutil.copy2(str(src), str(dst)); n += 1", "            shutil.copy2(str(src), str(dst))
            n += 1")
c = c.replace("                shutil.copy2(str(f), str(t)); n += 1", "                shutil.copy2(str(f), str(t))
                n += 1")
c = c.replace("    if n: print(f\"[sync] {n} config/template files synced.\")", "    if n:
        print(f\"[sync] {n} config/template files synced.\")")
c = c.replace('        print("Usage: python sync_plugin_cache.py <project_root>"); sys.exit(1)', '        print("Usage: python sync_plugin_cache.py <project_root>")
        sys.exit(1)')
c = c.replace('        print(f"ERROR: {root} is not a directory"); sys.exit(1)', '        print(f"ERROR: {root} is not a directory")
        sys.exit(1)')
with open(p, "w", encoding="utf-8") as f: f.write(c)
print("FIX3: sync_plugin_cache.py")

# Fix #4: _hook_bash.py — split inline statements
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\hooks\_hook_bash.py"
with open(p, "r", encoding="utf-8") as f: c = f.read()

c = c.replace("    if not buf: return False", "    if not buf:
        return False")
c = c.replace("    word = ''.join(buf); buf.clear()", "    word = ''.join(buf)
    buf.clear()")
c = c.replace("    if not word or not is_first: return False", "    if not word or not is_first:
        return False")
c = c.replace("    if '/' in word: word = word.rsplit('/', 1)[-1]", "    if '/' in word:
        word = word.rsplit('/', 1)[-1]")
c = c.replace("    if '=' in word and word.split('=', 1)[0].isidentifier(): return True", "    if '=' in word and word.split('=', 1)[0].isidentifier():
        return True")
c = c.replace("    if word in ('sudo', 'exec', 'command', 'nohup', 'time', 'nice', 'env'): return True", "    if word in ('sudo', 'exec', 'command', 'nohup', 'time', 'nice', 'env'):
        return True")
with open(p, "w", encoding="utf-8") as f: f.write(c)
print("FIX4: _hook_bash.py")

# Fix #5: tool_constraint_check.py — split inline statements
p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\tools\tool_constraint_check.py"
with open(p, "r", encoding="utf-8") as f: c = f.read()

c = c.replace("    if target_path: ctx[\"target_path\"] = target_path", "    if target_path:
        ctx[\"target_path\"] = target_path")
c = c.replace("    if allowed_paths: ctx[\"allowed_paths\"] = allowed_paths", "    if allowed_paths:
        ctx[\"allowed_paths\"] = allowed_paths")
c = c.replace("        try: ctx[\"current_phase\"] = Phase(current_phase)", "        try:
            ctx[\"current_phase\"] = Phase(current_phase)")
c = c.replace("        except ValueError: pass", "        except ValueError:
            pass")
c = c.replace("        try: ctx[\"target_phase\"] = Phase(target_phase)", "        try:
            ctx[\"target_phase\"] = Phase(target_phase)")
with open(p, "w", encoding="utf-8") as f: f.write(c)
print("FIX5: tool_constraint_check.py")

