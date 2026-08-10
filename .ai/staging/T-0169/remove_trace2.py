#!/usr/bin/env python3
"""remove_trace2.py — 按行精确删除 TRACE2（6 空格缩进变体）"""
from pathlib import Path

GG = Path(r"C:\Users\Administrator\.qoder-cn\hooks\scripts\gate-guard.js")

def main() -> int:
    lines = GG.read_text(encoding="utf-8").split("\n")
    out = [ln for ln in lines if "[TRACE2]" not in ln and "[TRACE]" not in ln and "[TRACE3]" not in ln]
    removed = len(lines) - len(out)
    GG.write_text("\n".join(out), encoding="utf-8")
    print(f"[fix] removed {removed} TRACE line(s)")

    import subprocess
    r = subprocess.run(["node", "-c", str(GG)], capture_output=True, text=True, encoding="utf-8")
    print("[ok] syntax OK" if r.returncode == 0 else "[err] " + r.stderr[:200])
    return 0 if r.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
