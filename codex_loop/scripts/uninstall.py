"""
uninstall.py — Loop 工程插件卸载脚本。

从项目中移除 Loop 治理配置，备份 .ai/ 目录。

用法：
    python uninstall.py --project-root <目标项目根目录>
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Loop 工程插件——卸载")
    parser.add_argument("--project-root", required=True, help="目标项目根目录")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    backup_dir = project_root / f".ai.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    ai_dir = project_root / ".ai"
    if ai_dir.exists():
        shutil.move(str(ai_dir), str(backup_dir))
        print(f"[uninstall] .ai/ 已备份到 {backup_dir}")

    zcode_config = project_root / ".zcode" / "skills" / "loop-governance"
    if zcode_config.exists():
        shutil.rmtree(zcode_config)
        print("[uninstall] .zcode/skills/loop-governance/ 已移除")

    print("\n[uninstall] ✅ Loop 工程治理已从项目中移除。")


if __name__ == "__main__":
    main()
