"""
Tests for T-0104 设计-5 memory_injection switch (S4+ 调用点开启记忆注入)。

Covers:
- config 读取：enabled=true（phases 内 S4+ → 注入）/ enabled=false（不注入）
   / 配置缺失（fail-closed 不注入，行为与现状完全一致）
- role_orchestrator.build_dispatch_manifest：S4+ 阶段显式传
  include_memories=True, memory_limit=5；enabled=false 时传 False
- context_packager.build_context：include_memories=True 时上下文含
  "相关经验（Related Memories）"节（渲染格式与 context_loader 一致），
  默认 False 时无该节（零行为变化）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.context_packager import build_context  # noqa: E402
from loop_core.role_orchestrator import (  # noqa: E402
    _load_memory_injection_config,
    _memory_injection_for,
    build_dispatch_manifest,
)

CONFIG_REPO_REL = Path("skills") / "loop-governance" / "config.yaml"


def _write_config(root: Path, enabled: bool, phases=None, memory_limit=5) -> None:
    """Write a minimal loop-governance config.yaml with a memory_injection node."""
    path = root / CONFIG_REPO_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"version: 1\nmemory_injection:\n  enabled: {str(enabled).lower()}\n"
    body += f"  phases: {phases or []}\n  memory_limit: {memory_limit}\n"
    path.write_text(body, encoding="utf-8")


def _seed_knowledge(root: Path, n: int = 3) -> None:
    """Seed the knowledge store with n entries via put_entry (idempotent)."""
    from loop_core.knowledge_store import put_entry

    for i in range(n):
        put_entry(
            root,
            kind="lesson",
            source_type="task",
            source_id=f"T-00{i:02d}",
            task_id=f"T-00{i:02d}",
            tags=["上下文压缩"],
            content=f"经验 {i}: 同款上下文压缩先压缩再注入，token 占用减半",
        )


@pytest.fixture
def tmp_root():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestMemoryInjectionConfig:
    def test_enabled_true_with_phases(self, tmp_root):
        _write_config(tmp_root, True, ["S4", "S5", "S6", "S8", "S9", "S10"], 5)
        cfg = _load_memory_injection_config(tmp_root)
        assert cfg["enabled"] is True
        assert cfg["phases"] == ["S4", "S5", "S6", "S8", "S9", "S10"]
        assert cfg["memory_limit"] == 5

    def test_enabled_false_disables(self, tmp_root):
        _write_config(tmp_root, False, ["S4", "S5", "S6"], 5)
        assert _memory_injection_for("S4-implementation", tmp_root) == (False, 5)

    def test_missing_config_fail_closed(self, tmp_root):
        """配置缺失 → 不注入（与现状一致）。"""
        assert _memory_injection_for("S4-implementation", tmp_root) == (False, 5)

    def test_corrupt_config_fail_closed(self, tmp_root):
        path = tmp_root / CONFIG_REPO_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not: [valid: yaml\n  :::", encoding="utf-8")
        assert _memory_injection_for("S4-implementation", tmp_root) == (False, 5)

    def test_phase_prefix_matching(self, tmp_root):
        _write_config(tmp_root, True, ["S4", "S10"], 5)
        # 完整阶段名 "S4-implementation" ↔ 配置短名 "S4"
        assert _memory_injection_for("S4-implementation", tmp_root) == (True, 5)
        assert _memory_injection_for("S10-performance", tmp_root) == (True, 5)
        # phases 之外的阶段不注入
        assert _memory_injection_for("S3-interface", tmp_root) == (False, 5)
        assert _memory_injection_for("S11-maintenance", tmp_root) == (False, 5)

    def test_memory_limit_override(self, tmp_root):
        _write_config(tmp_root, True, ["S4"], 3)
        assert _memory_injection_for("S4-implementation", tmp_root) == (True, 3)


class TestDispatchPassesIncludeMemories:
    def test_s4_dispatches_with_memories_when_enabled(self, tmp_root, monkeypatch):
        _write_config(tmp_root, True, ["S4", "S5", "S6", "S8", "S9", "S10"], 5)
        captured = {}

        def fake_load(role_id, project_root=".", task_id="", extra_files=None,
                      *, include_memories=False, memory_limit=5):
            captured.update(
                include_memories=include_memories, memory_limit=memory_limit
            )
            return "PROMPT"

        monkeypatch.setattr(
            "loop_core.role_loader.load_role_prompt_with_context", fake_load
        )
        manifest = build_dispatch_manifest(str(tmp_root), "S4-implementation",
                                           task_id="T-0104")
        assert manifest["subagents"], "S4 应派发 developer"
        assert captured["include_memories"] is True
        assert captured["memory_limit"] == 5

    def test_s3_no_memories(self, tmp_root, monkeypatch):
        _write_config(tmp_root, True, ["S4", "S5", "S6", "S8", "S9", "S10"], 5)
        captured = {}

        def fake_load(role_id, project_root=".", task_id="", extra_files=None,
                      *, include_memories=False, memory_limit=5):
            captured.update(
                include_memories=include_memories, memory_limit=memory_limit
            )
            return "PROMPT"

        monkeypatch.setattr(
            "loop_core.role_loader.load_role_prompt_with_context", fake_load
        )
        manifest = build_dispatch_manifest(str(tmp_root), "S3-interface",
                                           task_id="T-0104")
        assert manifest["subagents"]
        assert captured["include_memories"] is False

    def test_disabled_switch_identical_to_status_quo(self, tmp_root, monkeypatch):
        """enabled=false → include_memories=False（行为与现状完全一致）。"""
        _write_config(tmp_root, False, ["S4", "S5", "S6", "S8", "S9", "S10"], 5)
        captured = []

        def fake_load(role_id, project_root=".", task_id="", extra_files=None,
                      *, include_memories=False, memory_limit=5):
            captured.append((include_memories, memory_limit))
            return "PROMPT"

        monkeypatch.setattr(
            "loop_core.role_loader.load_role_prompt_with_context", fake_load
        )
        build_dispatch_manifest(str(tmp_root), "S4-implementation", task_id="T-0104")
        assert captured == [(False, 5)]


class TestContextPackagerInjection:
    def test_default_no_memory_section(self, tmp_root):
        _seed_knowledge(tmp_root, 2)
        ctx = build_context(str(tmp_root), "developer")
        assert "相关经验（Related Memories）" not in ctx
        assert "execution_mode: SIMULATED_MAIN_SESSION" in ctx

    def test_include_memories_adds_section(self, tmp_root):
        _seed_knowledge(tmp_root, 2)
        ctx = build_context(str(tmp_root), "developer", include_memories=True)
        assert "## 相关经验（Related Memories）" in ctx

    def test_memory_limit_caps_entries(self, tmp_root):
        _seed_knowledge(tmp_root, 5)
        ctx = build_context(
            str(tmp_root), "developer", include_memories=True, memory_limit=2
        )
        section = ctx.split("## 相关经验（Related Memories）", 1)[1]
        bullets = [ln for ln in section.splitlines() if ln.startswith("- (")]
        assert len(bullets) == 2

    def test_empty_store_noop(self, tmp_root):
        """空召回 = 无节 = no-op（与 context_loader 语义一致）。"""
        ctx = build_context(str(tmp_root), "developer", include_memories=True)
        assert "相关经验（Related Memories）" not in ctx

    def test_malformed_store_fail_closed(self, tmp_root):
        """include_memories=True 且 store 损坏 → 抛 KnowledgeStoreError。"""
        from loop_core.knowledge_store import KnowledgeStoreError

        kpath = tmp_root / ".ai" / "evidence" / "knowledge" / "knowledge-store.yaml"
        kpath.parent.mkdir(parents=True, exist_ok=True)
        kpath.write_text("schema: knowledge_store\nentries: [broken", encoding="utf-8")
        with pytest.raises(KnowledgeStoreError):
            build_context(str(tmp_root), "developer", include_memories=True)
