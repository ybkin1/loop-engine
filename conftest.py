import sys
from pathlib import Path

# 将项目根注入 sys.path，消除每个测试文件手动设 path 的碎片
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
