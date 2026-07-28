import os
base = r"C:\Users\Administrator\.codex\loop-engine-lab"

def fix(path, old, new):
    p = os.path.join(base, path)
    c = open(p, encoding="utf-8").read()
    c = c.replace(old, new)
    open(p, "w", encoding="utf-8").write(c)
    return old in open(p, encoding="utf-8").read() == False if old in c else True

# enforcement_hub.py
fix("codex_loop/core/enforcement_hub.py",
    "if developer_role in cls.DEVELOPMENT_ROLES: dev_domains.append",
    "if developer_role in cls.DEVELOPMENT_ROLES:\n            dev_domains.append")
fix("codex_loop/core/enforcement_hub.py",
    "if developer_role in cls.QUALITY_ROLES: dev_domains.append",
    "if developer_role in cls.QUALITY_ROLES:\n            dev_domains.append")
fix("codex_loop/core/enforcement_hub.py",
    "if developer_role in cls.GOVERNANCE_ROLES: dev_domains.append",
    "if developer_role in cls.GOVERNANCE_ROLES:\n            dev_domains.append")
fix("codex_loop/core/enforcement_hub.py",
    "if reviewer_role in cls.DEVELOPMENT_ROLES: rev_domains.append",
    "if reviewer_role in cls.DEVELOPMENT_ROLES:\n            rev_domains.append")
fix("codex_loop/core/enforcement_hub.py",
    "if reviewer_role in cls.QUALITY_ROLES: rev_domains.append",
    "if reviewer_role in cls.QUALITY_ROLES:\n            rev_domains.append")
fix("codex_loop/core/enforcement_hub.py",
    "if reviewer_role in cls.GOVERNANCE_ROLES: rev_domains.append",
    "if reviewer_role in cls.GOVERNANCE_ROLES:\n            rev_domains.append")
print("1: enforcement_hub DONE")
