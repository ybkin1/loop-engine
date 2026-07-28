import re
path = r"C:\Users\Administrator\.codex\loop-engine-lab\codex_loop\evidence\execution_ledger.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    '"actors_differ": False,',
    '"actors_differ": False,\n            "sessions_differ": False,'
)

old = '            result["fingerprints_differ"] = (\n                d.prompt_fingerprint != r.prompt_fingerprint\n            )'
new = '            result["sessions_differ"] = d.session_id != r.session_id\n            if not result["sessions_differ"]:\n                result["valid"] = False\n                result["violations"].append(\n                    "Same session for dev and reviewer -- not independently isolated"\n                )\n            result["fingerprints_differ"] = (\n                d.prompt_fingerprint != r.prompt_fingerprint\n            )'
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("DONE")
