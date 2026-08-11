"""
_hook_emergency.py — 逃生开关（T-0177 H2 加固）。

原实现（T-0168）仅检查 ~/.loop-engine-emergency 文件存在：无内容校验、无
TTL、跨项目全局生效、无审计留痕（评审 H2）。加固后：
- env LOOP_ENGINE_EMERGENCY=1（宿主进程级，人触发）→ 立即生效（保留）
- 文件 ~/.loop-engine-emergency → 内容校验 + 24h TTL + 审计留痕
- fail-open：任何读取/解析异常都视为激活（逃生不可被阻断）

本模块由 hook_common re-export（emergency_active），保持公开符号面不变。
"""
import os
import time
from datetime import datetime
from pathlib import Path

EMERGENCY_FILE = Path.home() / ".loop-engine-emergency"
EMERGENCY_TTL_SECONDS = 24 * 3600
EMERGENCY_AUDIT_LOG = Path.home() / ".loop-engine-emergency.log"
_EMERGENCY_VALID_CONTENT = {"1", "active", "on"}
_emergency_last_audit: float = 0.0


def _emergency_audit(event: str, detail: str = "") -> None:
    """逃生事件审计留痕（~/.loop-engine-emergency.log）；60s 窗口去重防刷屏。

    审计失败静默（逃生可用性优先于审计完整性）。
    """
    global _emergency_last_audit
    now = time.time()
    if now - _emergency_last_audit < 60:
        return
    _emergency_last_audit = now
    try:
        with open(EMERGENCY_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now().isoformat(timespec='seconds')} {event} "
                f"pid={os.getpid()} cwd={os.getcwd()} {detail}\n"
            )
    except OSError:
        pass


def _emergency_file_active() -> bool:
    """文件逃生判定：内容校验 + TTL；读取异常 fail-open（视为激活）。"""
    try:
        f = EMERGENCY_FILE
        if not f.exists():
            return False
        content = f.read_text(encoding="utf-8").strip()
        # 内容校验：非标记内容不触发（防止误创建的空文件/无关内容触发逃生）
        if content not in _EMERGENCY_VALID_CONTENT:
            return False
        # TTL：文件创建/修改距今超过 24h 自动失效（临时逃生，不永久全局绕过）
        age = time.time() - f.stat().st_mtime
        return age <= EMERGENCY_TTL_SECONDS
    except OSError:
        # fail-open：逃生开关读取失败时视为激活，逃生不可被阻断
        return True


def emergency_active() -> bool:
    """逃生模式判定（统一入口，gate_guard/loop_enforcement 共享）。

    env LOOP_ENGINE_EMERGENCY=1 → 立即生效（宿主进程级，人触发）。
    文件逃生 → 内容校验 + 24h TTL + 审计留痕。
    """
    if os.environ.get("LOOP_ENGINE_EMERGENCY") == "1":
        _emergency_audit("env-activated")
        return True
    active = _emergency_file_active()
    if active:
        _emergency_audit("file-activated")
    return active
