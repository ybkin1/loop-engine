#!/usr/bin/env python3
"""update_handoff_wire.py — AC-05：HANDOFF-qoder-loop.md 追加接线说明"""
from pathlib import Path

H = Path(r"C:\Users\Administrator\.qoder-cn\HANDOFF-qoder-loop.md")

def main() -> int:
    t = H.read_text(encoding="utf-8")
    if "## 八、Qoder 接线记录" in t:
        print("[same] wiring section already present")
        return 0

    block = """

---

## 八、Qoder 接线记录（T-0169，2026-08-10）

### 接线完成内容

1. **真实配置**：`AppData\\Roaming\\QoderCN\\User\\settings.json` 已追加：
   - PreToolUse Write|Edit：gate-guard / path-guard / role-isolation /
     ledger-guard / import-guard / output_quality_guard
   - PreToolUse Bash：gate-guard / path-guard / role-isolation / ledger-guard
   - UserPromptSubmit：auto-activate / template-injector / session-brief
   - Stop：session-summary
   - mcpServers：loop-engineering（→ loop-engine-lab/dist/src/server/index.js）
   - **clawd-on-desk 既有注册全部保留**（只追加不覆盖）
2. **备份**：`settings.json.bak-loop-20260810`（改前快照，回滚用）
3. **镜像**：`.qoder-cn/settings.json` 已同步

### 执行层关键修复（接线验证发现）

- **hook_common.js loadGates 解析缺陷**：`extractYamlObjectList` 的
  listRegex 要求列表行以空白开头，ZCode 生成的 gates.yaml 是顶格
  `- id:` → 解析 0 条 → `isLoopActive=false` → **所有 JS hooks 在真实
  项目上失效**（此前深度分析"JS hooks 语义缩水"的实锤）。
  已修复两处：① listRegex 兼容顶格列表；② 列表项识别 `/^\\s*-\\s+/`。
  修复后实测：isLoopActive=true、gate-guard 任务范围外写入 exit 2 拦截、
  import-guard 裸包渐进升级（2 次后 exit 2 硬阻断）全部生效。

### 生效要求

- **settings.json 修改需重启 Qoder** 才能加载新 hooks/MCP
- hooks/scripts 脚本修改即时生效（无需重启）
- 回滚：复制 `settings.json.bak-loop-20260810` 覆盖 settings.json 后重启

### 验证记录

- AC-01/02：loop hooks 全部注册 + clawd 保留 + MCP 指向正确 ✅
- AC-03：output_quality_guard 密钥 deny / gate-guard 范围外拦截 /
  import-guard 渐进升级 全部实测 ✅
- AC-04：MCP tools/list 返回 37 工具（含 loop_output_quality /
  loop_quality_gate / loop_state）✅
"""

    H.write_text(t.rstrip() + "\n" + block, encoding="utf-8")
    print("[patch] HANDOFF-qoder-loop.md wiring section appended")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
