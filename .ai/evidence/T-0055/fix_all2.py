import re, os
base = r"C:\Users\Administrator\.codex\loop-engine-lab"

fixes = {
    "codex_loop\\core\\enforcement_hub.py": [
        ("if developer_role in cls.DEVELOPMENT_ROLES: dev_domains.append("development")",
         "if developer_role in cls.DEVELOPMENT_ROLES:
            dev_domains.append("development")"),
        ("if developer_role in cls.QUALITY_ROLES: dev_domains.append("quality")",
         "if developer_role in cls.QUALITY_ROLES:
            dev_domains.append("quality")"),
        ("if developer_role in cls.GOVERNANCE_ROLES: dev_domains.append("governance")",
         "if developer_role in cls.GOVERNANCE_ROLES:
            dev_domains.append("governance")"),
        ("if reviewer_role in cls.DEVELOPMENT_ROLES: rev_domains.append("development")",
         "if reviewer_role in cls.DEVELOPMENT_ROLES:
            rev_domains.append("development")"),
        ("if reviewer_role in cls.QUALITY_ROLES: rev_domains.append("quality")",
         "if reviewer_role in cls.QUALITY_ROLES:
            rev_domains.append("quality")"),
        ("if reviewer_role in cls.GOVERNANCE_ROLES: rev_domains.append("governance")",
         "if reviewer_role in cls.GOVERNANCE_ROLES:
            rev_domains.append("governance")"),
    ],
    "codex_loop\\governance\\repair_continuity.py": [
        ("errors.append(f"missing: {item['path']}"); continue",
         "errors.append(f"missing: {item['path']}")
            continue"),
        ("errors.append(f"read error: {item['path']}: {e}"); continue",
         "errors.append(f"read error: {item['path']}: {e}")
            continue"),
        ("item["sha256"] = ah; item["size"] = sz; fixed += 1",
         "item["sha256"] = ah
            item["size"] = sz
            fixed += 1"),
        ("print("Usage: python repair_continuity.py <project_root>"); sys.exit(1)",
         "print("Usage: python repair_continuity.py <project_root>")
        sys.exit(1)"),
        ("print(f"ERROR: not a directory: {root}"); sys.exit(1)",
         "print(f"ERROR: not a directory: {root}")
        sys.exit(1)"),
    ],
    "codex_loop\\governance\\sync_plugin_cache.py": [
        ("    if not local.is_dir(): return 0",
         "    if not local.is_dir():
        return 0"),
        ("        if f.name.startswith("__"): continue",
         "        if f.name.startswith("__"):
            continue"),
        ("            shutil.copy2(str(f), str(t)); n += 1",
         "            shutil.copy2(str(f), str(t))
            n += 1"),
        ("    if n: print(f"[sync] {n} hook scripts synced.")",
         "    if n:
        print(f"[sync] {n} hook scripts synced.")"),
        ("    if not local.is_dir(): return 0",
         "    if not local.is_dir():
        return 0"),
        ("            shutil.copy2(str(src), str(dst)); n += 1",
         "            shutil.copy2(str(src), str(dst))
            n += 1"),
        ("                shutil.copy2(str(f), str(t)); n += 1",
         "                shutil.copy2(str(f), str(t))
                n += 1"),
        ("    if n: print(f"[sync] {n} config/template files synced.")",
         "    if n:
        print(f"[sync] {n} config/template files synced.")"),
        ("print("Usage: python sync_plugin_cache.py <project_root>"); sys.exit(1)",
         "print("Usage: python sync_plugin_cache.py <project_root>")
        sys.exit(1)"),
        ("print(f"ERROR: {root} is not a directory"); sys.exit(1)",
         "print(f"ERROR: {root} is not a directory")
        sys.exit(1)"),
    ],
    "codex_loop\\hooks\\_hook_bash.py": [
        ("    if not buf: return False",
         "    if not buf:
        return False"),
        ("    word = "".join(buf); buf.clear()",
         "    word = "".join(buf)
    buf.clear()"),
        ("    if not word or not is_first: return False",
         "    if not word or not is_first:
        return False"),
        ("    if "/" in word: word = word.rsplit("/", 1)[-1]",
         "    if "/" in word:
        word = word.rsplit("/", 1)[-1]"),
        ("    if "=" in word and word.split("=", 1)[0].isidentifier(): return True",
         "    if "=" in word and word.split("=", 1)[0].isidentifier():
        return True"),
        ("    if word in ("sudo", "exec", "command", "nohup", "time", "nice", "env"): return True",
         "    if word in ("sudo", "exec", "command", "nohup", "time", "nice", "env"):
        return True"),
    ],
    "codex_loop\\tools\\tool_constraint_check.py": [
        ("    if target_path: ctx["target_path"] = target_path",
         "    if target_path:
        ctx["target_path"] = target_path"),
        ("    if allowed_paths: ctx["allowed_paths"] = allowed_paths",
         "    if allowed_paths:
        ctx["allowed_paths"] = allowed_paths"),
        ("        try: ctx["current_phase"] = Phase(current_phase)",
         "        try:
            ctx["current_phase"] = Phase(current_phase)"),
        ("        except ValueError: pass",
         "        except ValueError:
            pass"),
        ("        try: ctx["target_phase"] = Phase(target_phase)",
         "        try:
            ctx["target_phase"] = Phase(target_phase)"),
        ("        except ValueError: pass",
         "        except ValueError:
            pass"),
    ],
}

total = 0
for rel_path, replacements in fixes.items():
    p = os.path.join(base, rel_path)
    c = open(p, encoding="utf-8").read()
    for old, new in replacements:
        if old in c:
            c = c.replace(old, new)
            total += 1
    open(p, "w", encoding="utf-8").write(c)
    print(f"OK: {os.path.basename(rel_path)}")
print(f"TOTAL FIXES: {total}")
