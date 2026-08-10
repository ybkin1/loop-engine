#!/usr/bin/env python3
"""run_continuity_producer.py — 包装执行 continuity_producer（解决模块路径）"""
import sys
from pathlib import Path

TOOLS = Path(r"c:\Users\Administrator\ZCodeProject\loop-engine\.zcode\tools")
sys.path.insert(0, str(TOOLS))
sys.argv = ["continuity_producer.py", r"c:\Users\Administrator\ZCodeProject\loop-engine"]

import continuity_producer  # noqa: E402

continuity_producer.main()
