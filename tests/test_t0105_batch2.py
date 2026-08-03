"""
T-0105 批 2 — T-0104 独立审查 P3 四项修复测试。

Covers:
- B-4-1 context_packager 记忆召回过滤：recall 透传 task_id/gate_id/tag
  （AND 组合，None = 不过滤 → 与 T-0104 现状一致）；role_orchestrator
  派发 S4+ 时透传当前 task_id
- B-4-2 memory_injection 配置校验：phases 必须为 list（字符串视为非法 →
  回退 disabled）；memory_limit 非正数/非数字 → 默认 5（fail-closed 保持）
- B-4-3 evidence-manifest 时序约定文档化：.ai/CONTRACTS.md 含完成流程约定
- B-4-4 _load_memory_injection_config 进程内读盘缓存：
  首次读盘 / 缓存命中（mtime 不变）/ mtime 变化重读 / 读取失败清缓存
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.context_packager import build_context  # noqa: E402
from loop_core.role_orchestrator import (  # noqa: E402
    _CONFIG_CACHE,
    _load_memory_injection_config,
    _memory_injection_for,
    _validated_memory_limit,
    _validated_phases,
    build_dispatch_manifest,
)

CONFIG_REPO_REL = Path("skills") / "loop-governance" / "config.yaml"


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """每个测试后清空模块级配置缓存，避免跨测试污染。"""
    yield
    _CONFIG_CACHE.clear()


@pytest.fixture
def tmp_root():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _write_config(root: Path, enabled: bool, phases=None, memory_limit=5) -> Path:
    """Write a minimal loop-governance config.yaml with a memory_injection node."""
    path = root / CONFIG_REPO_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"version: 1\nmemory_injection:\n  enabled: {str(enabled).lower()}\n"
    if isinstance(phases, str):
        body += f"  phases: {phases}\n"
    else:
        body += f"  phases: {phases or []}\n"
    body += f"  memory_limit: {memory_limit}\n"
    path.write_text(body, encoding="utf-8")
    return path


def _seed_knowledge(root: Path) -> None:
    """Seed two task entries + one gate entry with distinct filters."""
    from loop_core.knowledge_store import put_entry

    put_entry(
        root,
        kind="lesson",
        source_type="task",
        source_id="T-00A",
        task_id="T-00A",
        tags=["上下文压缩"],
        content="A 任务经验：先压缩再注入",
    )
    put_entry(
        root,
        kind="lesson",
        source_type="task",
        source_id="T-00B",
        task_id="T-00B",
        tags=["回归"],
        content="B 任务经验：回归基线 0 failed",
    )
    put_entry(
        root,
        kind="decision",
        source_type="gate",
        source_id="G-TEST-GATE",
        task_id="T-00C",
        tags=["门禁"],
        content="G 门禁经验：用户 Gate 前不推进",
    )


# ── B-4-1 记忆召回过滤 ────────────────────────────────────────────────────

class TestRecallFilteringB41:
    def test_task_id_filter_isolates_task_memories(self, tmp_root):
        """task_id 透传 → 只召回该任务的记忆（消除跨任务注入）。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(
            str(tmp_root), "developer", task_id="T-00A", include_memories=True
        )
        assert "A 任务经验" in ctx
        assert "B 任务经验" not in ctx
        assert "G 门禁经验" not in ctx

    def test_no_task_id_is_status_quo_unfiltered(self, tmp_root):
        """task_id 缺失（"" → None）→ 不过滤，与 T-0104 现状一致。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(
            str(tmp_root), "developer", include_memories=True
        )
        assert "A 任务经验" in ctx
        assert "B 任务经验" in ctx
        assert "G 门禁经验" in ctx

    def test_gate_id_filter(self, tmp_root):
        """memory_gate_id 透传 → 只召回该门禁的记忆。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(
            str(tmp_root), "developer", include_memories=True,
            memory_gate_id="G-TEST-GATE",
        )
        assert "G 门禁经验" in ctx
        assert "A 任务经验" not in ctx
        assert "B 任务经验" not in ctx

    def test_tag_filter(self, tmp_root):
        """memory_tag 透传 → 只召回带该标签的记忆。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(
            str(tmp_root), "developer", include_memories=True,
            memory_tag="上下文压缩",
        )
        assert "A 任务经验" in ctx
        assert "B 任务经验" not in ctx

    def test_combined_filters_and_combine(self, tmp_root):
        """task_id + tag 组合 = AND（T-00A 带 上下文压缩 标签）。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(
            str(tmp_root), "developer", task_id="T-00A",
            include_memories=True, memory_tag="上下文压缩",
        )
        assert "A 任务经验" in ctx
        assert "B 任务经验" not in ctx
        ctx2 = build_context(
            str(tmp_root), "developer", task_id="T-00A",
            include_memories=True, memory_tag="回归",
        )
        assert "A 任务经验" not in ctx2  # AND：T-00A 无 回归 标签

    def test_default_include_memories_false_untouched(self, tmp_root):
        """include_memories=False（默认）→ 无记忆节（零行为变化）。"""
        _seed_knowledge(tmp_root)
        ctx = build_context(str(tmp_root), "developer", task_id="T-00A")
        assert "相关经验（Related Memories）" not in ctx

    def test_dispatch_forwards_task_id(self, tmp_root, monkeypatch):
        """role_orchestrator 派发 S4+ 时把当前 task_id 传入 prompt 构建链。"""
        _write_config(tmp_root, True, ["S4"], 5)
        captured = {}

        def fake_load(role_id, project_root=".", task_id="", extra_files=None,
                      *, include_memories=False, memory_limit=5):
            captured.update(
                include_memories=include_memories,
                memory_limit=memory_limit,
                task_id=task_id,
            )
            return "PROMPT"

        monkeypatch.setattr(
            "loop_core.role_loader.load_role_prompt_with_context", fake_load
        )
        manifest = build_dispatch_manifest(str(tmp_root), "S4-implementation",
                                           task_id="T-00A")
        assert manifest["subagents"]
        assert captured["task_id"] == "T-00A"
        assert captured["include_memories"] is True


# ── B-4-2 配置校验 ────────────────────────────────────────────────────────

class TestConfigValidationB42:
    def test_phases_string_invalid_falls_back_disabled(self, tmp_root):
        """phases 误写为字符串（如 "S4"）→ 整体视为非法 → 回退 disabled。"""
        _write_config(tmp_root, True, phases='"S4"', memory_limit=5)
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg == {"enabled": False, "phases": [], "memory_limit": 5}
        assert _memory_injection_for("S4-implementation", tmp_root) == (False, 5)

    def test_phases_list_valid(self, tmp_root):
        """phases 为 list → 正常解析（不退化）。"""
        _write_config(tmp_root, True, ["S4", "S5"], 5)
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert cfg["phases"] == ["S4", "S5"]

    def test_phases_none_or_empty_ok(self, tmp_root):
        """phases 缺失/空 → []（enabled 仍按配置）。"""
        path = tmp_root / CONFIG_REPO_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "version: 1\nmemory_injection:\n  enabled: true\n"
            "  memory_limit: 5\n",
            encoding="utf-8",
        )
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert cfg["phases"] == []

    def test_memory_limit_non_positive_defaults_5(self, tmp_root):
        """memory_limit 0 / 负数 → 默认 5。"""
        _write_config(tmp_root, True, ["S4"], 0)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5
        _write_config(tmp_root, True, ["S4"], -3)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5

    def test_memory_limit_non_numeric_defaults_5(self, tmp_root):
        """memory_limit 非数字（字符串/None/bool）→ 默认 5。"""
        _write_config(tmp_root, True, ["S4"], '"abc"')
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5
        _write_config(tmp_root, True, ["S4"], True)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5

    def test_memory_limit_float_coerced(self, tmp_root):
        """memory_limit 浮点正数 → int 截断（沿用现状 int() 语义）。"""
        _write_config(tmp_root, True, ["S4"], 3.7)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 3

    def test_validator_units(self):
        assert _validated_phases(["S4", "S5"]) == ["S4", "S5"]
        assert _validated_phases("S4") is None
        assert _validated_phases(None) is None
        assert _validated_memory_limit(5) == 5
        assert _validated_memory_limit(0) == 5
        assert _validated_memory_limit(-1) == 5
        assert _validated_memory_limit("x") == 5
        assert _validated_memory_limit(True) == 5

    def test_fail_closed_semantics_kept(self, tmp_root):
        """损坏配置仍 fail-closed（缓存清空 + 回退默认）。"""
        path = tmp_root / CONFIG_REPO_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not: [valid: yaml\n  :::", encoding="utf-8")
        assert _load_memory_injection_config(tmp_root) == {
            "enabled": False, "phases": [], "memory_limit": 5,
        }


# ── B-4-4 配置读盘缓存 ────────────────────────────────────────────────────

class TestConfigDiskCacheB44:
    def test_first_read_loads_from_disk(self, tmp_root):
        """首次读取 → 读盘解析并缓存。"""
        _write_config(tmp_root, True, ["S4"], 5)
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert len(_CONFIG_CACHE) == 1

    def test_cache_hit_ignores_content_change_same_mtime(self, tmp_root):
        """缓存命中：内容变化但 mtime 不变 → 仍返回旧值（不重读）。"""
        path = _write_config(tmp_root, True, ["S4"], 5)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5
        mtime = path.stat().st_mtime_ns
        # 同 mtime 覆盖写入新内容
        path.write_text(
            "version: 1\nmemory_injection:\n  enabled: true\n"
            "  phases: ['S4']\n  memory_limit: 9\n",
            encoding="utf-8",
        )
        os.utime(path, ns=(mtime, mtime))
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5

    def test_mtime_change_triggers_reread(self, tmp_root):
        """mtime 变化 → 重读新值。"""
        path = _write_config(tmp_root, True, ["S4"], 5)
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 5
        path.write_text(
            "version: 1\nmemory_injection:\n  enabled: true\n"
            "  phases: ['S4']\n  memory_limit: 9\n",
            encoding="utf-8",
        )
        # 新 mtime（比原值晚 1 秒）
        os.utime(path, ns=(path.stat().st_mtime_ns + 1_000_000_000,
                           path.stat().st_mtime_ns + 1_000_000_000))
        assert _load_memory_injection_config(tmp_root)["memory_limit"] == 9

    def test_failed_read_clears_cache_and_fails_closed(self, tmp_root):
        """读取失败 → 清缓存回退默认；修复后（mtime 变化）可重新读到有效值。"""
        path = _write_config(tmp_root, True, ["S4"], 5)
        assert _load_memory_injection_config(tmp_root)["enabled"] is True
        # 损坏文件 + 新 mtime → fail-closed
        path.write_text("not: [valid: yaml\n  :::", encoding="utf-8")
        os.utime(path, ns=(path.stat().st_mtime_ns + 1_000_000_000,
                           path.stat().st_mtime_ns + 1_000_000_000))
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg == {"enabled": False, "phases": [], "memory_limit": 5}
        # 缓存已清空（损坏结果不驻留）
        assert str(path) not in _CONFIG_CACHE
        # 修复后重新读盘
        path.write_text(
            "version: 1\nmemory_injection:\n  enabled: true\n"
            "  phases: ['S4']\n  memory_limit: 7\n",
            encoding="utf-8",
        )
        os.utime(path, ns=(path.stat().st_mtime_ns + 1_000_000_000,
                           path.stat().st_mtime_ns + 1_000_000_000))
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert cfg["memory_limit"] == 7

    def test_second_candidate_used_when_first_missing(self, tmp_root):
        """第一个候选路径缺失 → 读取安装副本（.zcode/skills/...）。"""
        installed = tmp_root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text(
            "version: 1\nmemory_injection:\n  enabled: true\n"
            "  phases: ['S6']\n  memory_limit: 4\n",
            encoding="utf-8",
        )
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert cfg["memory_limit"] == 4


# ── B-4-3 时序约定文档化 ──────────────────────────────────────────────────

class TestManifestTimingConventionB43:
    def test_convention_documented_in_contracts(self):
        """完成流程时序约定已写入 .ai/CONTRACTS.md（B-4-3 文档证据）。"""
        contracts = (
            Path(__file__).resolve().parent.parent / ".ai" / "CONTRACTS.md"
        )
        text = contracts.read_text(encoding="utf-8")
        assert "Completion Flow Conventions" in text
        assert "evidence-manifest" in text
        assert "test_manifest_t0095" in text
        assert "HANDOFF" in text
