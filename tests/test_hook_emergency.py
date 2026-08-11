"""
test_hook_emergency.py — T-0177 H2 逃生开关加固回归测试。

原实现（T-0168）：仅检查 ~/.loop-engine-emergency 文件存在 → 永久全局绕过，
无内容校验、无 TTL、无审计。加固后：
- env LOOP_ENGINE_EMERGENCY=1 → 立即生效（宿主进程级，保留）
- 文件内容必须是标记（1/active/on）才生效（内容校验）
- 文件 mtime 距今 ≤ 24h 才生效（TTL）
- 读取异常 → fail-open（逃生不可被阻断）
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hooks", "scripts")))

import pytest
import hook_common
import _hook_emergency


@pytest.fixture
def emergency_file(tmp_path, monkeypatch):
    """把逃生文件路径指向临时目录，保证测试隔离。

    hook_common 与 _hook_emergency 均 patch：实现引用 _hook_emergency 的
    模块全局（re-export 绑定同一对象），hook_common 符号保持一致。
    """
    f = tmp_path / ".loop-engine-emergency"
    monkeypatch.setattr(_hook_emergency, "EMERGENCY_FILE", f)
    monkeypatch.setattr(hook_common, "EMERGENCY_FILE", f)
    monkeypatch.setattr(_hook_emergency, "_emergency_last_audit", time.time() + 3600)
    monkeypatch.delenv("LOOP_ENGINE_EMERGENCY", raising=False)
    return f


class TestEmergencyFileContent:
    def test_valid_content_activates(self, emergency_file):
        emergency_file.write_text("1", encoding="utf-8")
        assert hook_common.emergency_active() is True

    def test_active_word_activates(self, emergency_file):
        emergency_file.write_text("active", encoding="utf-8")
        assert hook_common.emergency_active() is True

    def test_empty_file_not_activate(self, emergency_file):
        emergency_file.write_text("", encoding="utf-8")
        assert hook_common.emergency_active() is False

    def test_garbage_content_not_activate(self, emergency_file):
        """H2 核心：非标记内容（误创建/无关内容）不得触发逃生。"""
        emergency_file.write_text("some random text", encoding="utf-8")
        assert hook_common.emergency_active() is False

    def test_missing_file_not_activate(self, emergency_file):
        assert hook_common.emergency_active() is False


class TestEmergencyTTL:
    def test_fresh_file_activates(self, emergency_file):
        emergency_file.write_text("1", encoding="utf-8")
        assert hook_common.emergency_active() is True

    def test_expired_file_not_activate(self, emergency_file):
        """H2 核心：超过 24h TTL 的逃生文件自动失效（不永久全局绕过）。"""
        emergency_file.write_text("1", encoding="utf-8")
        old = time.time() - hook_common.EMERGENCY_TTL_SECONDS - 60
        os.utime(emergency_file, (old, old))
        assert hook_common.emergency_active() is False


class TestEmergencyEnv:
    def test_env_activates_immediately(self, emergency_file, monkeypatch):
        monkeypatch.setenv("LOOP_ENGINE_EMERGENCY", "1")
        assert hook_common.emergency_active() is True

    def test_env_zero_does_not_activate(self, emergency_file, monkeypatch):
        monkeypatch.setenv("LOOP_ENGINE_EMERGENCY", "0")
        assert hook_common.emergency_active() is False


class TestEmergencyFailOpen:
    def test_unreadable_file_fail_open(self, emergency_file, monkeypatch):
        """读取异常必须 fail-open（逃生不可被阻断）。

        仅当目标文件是逃生文件时抛 OSError（不污染 pytest 内部 Path 使用）。
        """
        emergency_file.write_text("1", encoding="utf-8")
        orig_read = _hook_emergency.Path.read_text

        def read_text_raising(self, *a, **k):
            if self == emergency_file:
                raise OSError("permission denied")
            return orig_read(self, *a, **k)

        monkeypatch.setattr(_hook_emergency.Path, "read_text", read_text_raising)
        assert _hook_emergency.emergency_active() is True

    def test_oserror_in_file_check_activates(self, emergency_file, monkeypatch):
        """_emergency_file_active 内部 OSError → fail-open 返回 True。"""
        emergency_file.write_text("1", encoding="utf-8")
        orig_read = _hook_emergency.Path.read_text

        def read_text_raising(self, *a, **k):
            if self == emergency_file:
                raise OSError("boom")
            return orig_read(self, *a, **k)

        monkeypatch.setattr(_hook_emergency.Path, "read_text", read_text_raising)
        assert _hook_emergency._emergency_file_active() is True
