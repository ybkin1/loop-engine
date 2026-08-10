#!/usr/bin/env python3
"""remove_traces.py — 移除 gate-guard 中的临时 trace（TRACE/TRACE2/TRACE3）"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    t = GG.read_text(encoding="utf-8")
    traces = [
        "        process.stderr.write('[TRACE] allowedPaths=' + JSON.stringify(allowedPaths) + ' filePath=' + (filePath||'') + ' isFileWrite=' + isFileWrite + '\\n');\n",
        "       process.stderr.write('[TRACE2] cardPath=' + cardPath + ' raw=' + JSON.stringify(raw.slice(0, 60)) + '\\n');\n",
        "       process.stderr.write('[TRACE3] root=' + root + ' active=' + (state ? state.active_task_id : 'none') + '\\n');\n",
        "  process.stderr.write('[TRACE3] root=' + root + ' active=' + (state ? state.active_task_id : 'none') + '\\n');\n",
    ]
    removed = 0
    for tr in traces:
        if tr in t:
            t = t.replace(tr, "")
            removed += 1
    if removed == 0:
        print("[info] no traces found")
    GG.write_text(t, encoding="utf-8")
    print(f"[fix] removed {removed} trace line(s)")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    print("[ok] syntax OK" if r.returncode == 0 else "[err] " + r.stderr[:200])
    return 0 if r.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
