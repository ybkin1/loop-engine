#!/usr/bin/env python3
"""fix_handoff_text.py — 修正 HANDOFF 镜像与修复结论表述（T-0169 P1-2/P2-5）"""
from pathlib import Path

H = Path(r"C:\Users\Administrator\.qoder-cn\HANDOFF-qoder-loop.md")

def main() -> int:
    t = H.read_text(encoding="utf-8")

    old1 = "3. **镜像**：`.qoder-cn/settings.json` 已同步"
    new1 = "3. **镜像说明**：`.qoder-cn/settings.json` 由 Qoder 插件管理（含 enabledPlugins），不覆盖；loop 配置以真实 settings.json 为准"
    if old1 in t:
        t = t.replace(old1, new1)
        print("[fix] mirror statement corrected")
    else:
        print("[info] mirror statement not found or already corrected")

    old2 = "修复后实测：isLoopActive=true、gate-guard 任务范围外写入 exit 2 拦截、\n  import-guard 裸包渐进升级（2 次后 exit 2 硬阻断）全部生效。"
    new2 = "修复后实测：isLoopActive=true、gates 解析 119/119、tasks 解析 150/150、\n  gate-guard pending gate 阶段阻断 exit 2、任务范围外写入阻断、\n  import-guard 裸包渐进升级（2 次后 exit 2 硬阻断）全部生效。"
    if old2 in t:
        t = t.replace(old2, new2)
        print("[fix] fix-conclusion statement corrected")
    else:
        print("[info] fix-conclusion statement not found or already corrected")

    H.write_text(t, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
