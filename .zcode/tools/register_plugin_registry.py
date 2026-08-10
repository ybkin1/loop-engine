#!/usr/bin/env python3
"""register_plugin_registry.py — 幂等登记 loop-governance 到 ZCode 官方市场捆绑清单

背景（T-0174 根因，2026-08-10 调查结论）：
  ZCode 的插件发现（scanOfficialCache）优先读 bundled-marketplace.json 的
  manifest.plugins 清单（lGr）；清单非空时**不扫描文件系统**。loop-governance
  是手工部署的缓存插件（从未进入官方清单），因此永远不被发现 → hookCount 0、
  loop-tools MCP 不加载——这就是"hooks 不接管"的真正根因（平台并非不支持
  插件 hooks，而是插件未登记）。

  修复 = 把 loop-governance 登记进 bundled-marketplace.json（name + cachePath）。
  ZCode 应用更新可能覆盖该文件 → 本工具幂等补丁（检测缺失即重新登记），
  建议在 ZCode 更新后运行一次。

用法：
  python register_plugin_registry.py [--apply]
    （缺省 dry-run：报告当前状态；--apply 实际写入，写前自动备份 .bak-<ts>）
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

MARKETPLACE = "zcode-plugins-official"
PLUGIN_NAME = "loop-governance"
PLUGIN_VERSION = "1.0.0"
PLUGIN_CACHE_PATH = (
    Path.home() / ".zcode" / "cli" / "plugins" / "cache" / "zcode-plugins-official"
    / PLUGIN_NAME / PLUGIN_VERSION
)

BUNDLED = Path.home() / ".zcode" / "cli" / "plugins" / "marketplaces" / MARKETPLACE / "bundled-marketplace.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    args = parser.parse_args()

    if not BUNDLED.exists():
        print(f"[error] bundled-marketplace.json 不存在: {BUNDLED}")
        return 1
    if not PLUGIN_CACHE_PATH.exists():
        print(f"[error] 插件缓存目录不存在: {PLUGIN_CACHE_PATH}")
        return 1

    data = json.loads(BUNDLED.read_text(encoding="utf-8"))
    manifest = data.get("manifest", {})
    plugs = manifest.get("plugins", [])
    names = [p.get("name") for p in plugs]
    present = PLUGIN_NAME in names

    if present:
        entry = next(p for p in plugs if p.get("name") == PLUGIN_NAME)
        print(f"[ok] {PLUGIN_NAME} 已在清单中（version={entry.get('version')}，无需修补）")
        return 0

    print(f"[warn] {PLUGIN_NAME} 不在清单（{len(plugs)} 项）——插件 hooks/MCP 不会被发现")
    if not args.apply:
        print("[dry-run] 未写入。用 --apply 登记：")
        print(f"  name={PLUGIN_NAME} version={PLUGIN_VERSION}")
        print(f"  cachePath={PLUGIN_CACHE_PATH.as_posix()}")
        return 2

    backup = BUNDLED.with_name(f"bundled-marketplace.json.bak-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(BUNDLED, backup)
    plugs.append({
        "cachePath": str(PLUGIN_CACHE_PATH).replace("\\", "\\\\"),
        "description": "Loop 工程治理 —— 把 AI 编码变成可交付、可验证、可维护的软件工程。提供角色协作、质量门禁、证据链和 Gate 状态机。",
        "name": PLUGIN_NAME,
        "source": "filesystem",
        "version": PLUGIN_VERSION,
    })
    BUNDLED.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"[ok] 已登记 {PLUGIN_NAME}（备份: {backup.name}）。重启 ZCode 后 hookCount 应 > 0。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
