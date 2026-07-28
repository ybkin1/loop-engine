
import os

def fix_enforcement_hub():
    p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\core\enforcement_hub.py"
    with open(p, "r") as f: c = f.read()
    old = 'if developer_role in cls.DEVELOPMENT_ROLES: dev_domains.append("development")
        if developer_role in cls.QUALITY_ROLES: dev_domains.append("quality")
        if developer_role in cls.GOVERNANCE_ROLES: dev_domains.append("governance")'
    if old in c:
        new = 'if developer_role in cls.DEVELOPMENT_ROLES:
            dev_domains.append("development")
        if developer_role in cls.QUALITY_ROLES:
            dev_domains.append("quality")
        if developer_role in cls.GOVERNANCE_ROLES:
            dev_domains.append("governance")'
        c = c.replace(old, new)
    old2 = 'if reviewer_role in cls.DEVELOPMENT_ROLES: rev_domains.append("development")
        if reviewer_role in cls.QUALITY_ROLES: rev_domains.append("quality")
        if reviewer_role in cls.GOVERNANCE_ROLES: rev_domains.append("governance")'
    if old2 in c:
        new2 = 'if reviewer_role in cls.DEVELOPMENT_ROLES:
            rev_domains.append("development")
        if reviewer_role in cls.QUALITY_ROLES:
            rev_domains.append("quality")
        if reviewer_role in cls.GOVERNANCE_ROLES:
            rev_domains.append("governance")'
        c = c.replace(old2, new2)
    with open(p, "w") as f: f.write(c)
    print("1: enforcement_hub")

def fix_repair_continuity():
    p = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\governance\repair_continuity.py"
    with open(p, "r") as f: c = f.read()
    c = c.replace('if not isinstance(item, dict) or "path" not in item: continue', 'if not isinstance(item, dict) or "path" not in item:
            continue')
    c = c.replace('errors.append(f"missing: {item[chr(39)+chr(39)path"+chr(39)+chr(39)+"]}"); continue', 'errors.append(f"missing: {item[\'path\']}")
            continue')
    with open(p, "w") as f: f.write(c)
    print("2: repair_continuity")

fix_enforcement_hub()

