"""
T-0109 F5 工具 capability 化 + T-0113 薄壳删除 + T-0114 B 组死工具删除 —
注册表 26 全覆盖 / 内联注册表 LIVE 断言 / 重复合并行为等价 / 白名单一致性
（AC-04 / AC-05）。

覆盖：
- capability_registry 26 工具元数据全覆盖（与 tools/*.py 一一对应）+
  audience/domain 分级。
- 薄壳删除（T-0113）：6 个薄壳 + 2 个 legacy 脚本不再可导入；MCP 注册表
  内联键（quality_gates_run/security_scan_run/…）仍 LIVE，_dispatch 返回
  与薄壳 era 相同输出形态（subprocess 注入 fake 输出）；evidence 工具
  in-process loop_core 为唯一实现。
- B 组死工具删除（T-0114）：tool_task_queue/tool_eval/loop_vertical_slice/
  loop_dispatch_role 4 个文件不再可导入。
- dashboard 四层合并：status_dashboard.Dashboard is dashboard_views.Dashboard
  （单一实现）+ 输出等价。
- AC-05 白名单一致性：GOVERNANCE_TOOL_DIRS（AST 提取）覆盖全部注册工具；
  hooks/ 仅 loop_enforcement.py 一处改动。
"""
from __future__ import annotations

import ast
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys_path_ready = False


def _ensure_paths():
    global sys_path_ready
    if not sys_path_ready:
        import sys
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        if str(PROJECT_ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        sys_path_ready = True


_ensure_paths()

from loop_core.capability_registry import (  # noqa: E402
    AUDIENCES,
    TOOL_CAPABILITY_MANIFEST,
    all_tool_names,
    build_tool_registry,
    tool_capability,
    tools_by_audience,
    tools_by_domain,
)


# ═══════════════════════════════════════════════════════════════════════════
# AC-04: 注册表 26 工具全覆盖
# ═══════════════════════════════════════════════════════════════════════════

class TestToolRegistryCoverage:
    def test_manifest_covers_every_tool_module(self):
        """tools/*.py 与注册表一一对应（26 = 26，无遗漏无多余）。"""
        on_disk = {p.name[:-3] for p in (PROJECT_ROOT / "tools").glob("*.py")}
        registered = set(TOOL_CAPABILITY_MANIFEST)
        assert on_disk == registered
        assert len(registered) == 26

    def test_all_tool_names_stable(self):
        names = all_tool_names()
        assert names == sorted(names)
        assert len(names) == 26

    def test_registry_snapshot_sealed_26(self):
        registry = build_tool_registry(PROJECT_ROOT)
        assert registry.sealed is True
        snapshot = registry.snapshot()
        assert len(snapshot.entries) == 26
        assert "server" in snapshot.entries
        assert snapshot.entries["server"].provider_id == "tool"

    def test_unknown_tool_fail_closed(self):
        with pytest.raises(LookupError):
            tool_capability("definitely_not_a_tool")


class TestToolRegistryGrouping:
    def test_every_tool_has_valid_audience_and_domain(self):
        for name, cap in TOOL_CAPABILITY_MANIFEST.items():
            assert cap.name == name
            assert cap.audience in AUDIENCES, f"{name} audience 非法: {cap.audience}"
            assert cap.domain, f"{name} 缺少 domain"

    def test_audience_grouping_counts(self):
        """三级 audience 均非空且互斥覆盖 26 个工具。"""
        grouped = {a: tools_by_audience(a) for a in AUDIENCES}
        assert sum(len(v) for v in grouped.values()) == 26
        assert all(grouped[a] for a in AUDIENCES)

    def test_domain_grouping(self):
        assert "governance" in {cap.domain for cap in TOOL_CAPABILITY_MANIFEST.values()}
        # 关键域抽查
        assert "tool_state" in tools_by_domain("governance")
        assert "tool_evidence_submit" in tools_by_domain("evidence")
        assert "loop_dashboard" in tools_by_domain("dashboard")


# ═══════════════════════════════════════════════════════════════════════════
# 薄壳删除（T-0113）：MCP 注册表内联键仍 LIVE —— 注入相同的 subprocess.run
# 假输出 → _dispatch 返回与薄壳 era 相同的输出形态（行为等价，AC-04）
# ═══════════════════════════════════════════════════════════════════════════

class TestInlineDispatchLive:
    """T-0113 删除 6 薄壳 + 2 legacy 后，内联注册表键（quality_gates_run /
    security_scan_run / dependency_analysis / contract_validate / cost_report
    / evidence_verify / evidence_freeze）仍 LIVE，输出形态与薄壳 era 一致。"""

    @pytest.fixture(autouse=True)
    def _fake_subprocess(self, monkeypatch):
        captured: dict[str, dict] = {}

        def fake_run(cmd, capture_output=True, text=True, timeout=None, **kw):
            captured["cmd"] = cmd
            payload = {"fake": "payload", "overall": "PASS", "n": 1}
            return subprocess.CompletedProcess(
                args=cmd, returncode=0,
                stdout=json.dumps(payload), stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        return captured

    def test_quality_gates_dispatch_live(self, _fake_subprocess):
        import server
        args = {"project_root": str(PROJECT_ROOT), "output_dir": "tmp-q"}
        assert server._dispatch("quality_gates_run", dict(args)) == \
            {"fake": "payload", "overall": "PASS", "n": 1}

    def test_security_scan_dispatch_live(self, _fake_subprocess):
        import server
        args = {"project_root": str(PROJECT_ROOT), "output_dir": "tmp-s"}
        assert server._dispatch("security_scan_run", dict(args)) == \
            {"fake": "payload", "overall": "PASS", "n": 1}

    def test_dependency_analysis_dispatch_live(self, _fake_subprocess):
        import server
        args = {"project_root": str(PROJECT_ROOT), "rules_file": None}
        assert server._dispatch("dependency_analysis", dict(args)) == \
            {"fake": "payload", "overall": "PASS", "n": 1}

    def test_contract_validate_dispatch_live(self, _fake_subprocess):
        import server
        args = {"project_root": str(PROJECT_ROOT), "contract_file": "c.json"}
        assert server._dispatch("contract_validate", dict(args)) == \
            {"fake": "payload", "overall": "PASS", "n": 1}

    def test_cost_report_dispatch_live(self, _fake_subprocess):
        import server
        args = {"project_root": str(PROJECT_ROOT)}
        assert server._dispatch("cost_report", dict(args)) == \
            {"fake": "payload", "overall": "PASS", "n": 1}

    def test_server_no_longer_imports_shell_modules(self):
        """薄壳消除实证：server.py 源码不再 import 6 个薄壳模块。"""
        source = (PROJECT_ROOT / "tools" / "server.py").read_text(encoding="utf-8")
        for shell in ("tool_quality_gates", "tool_security_scan",
                      "tool_dependency_analysis", "tool_contract_validate",
                      "tool_cost_tracker", "tool_evidence_chain"):
            assert f"from {shell} import" not in source, f"server.py 仍 import {shell}"

    def test_shell_modules_removed(self):
        """删除实证：T-0113 的 6 薄壳 + 2 legacy 与 T-0114 的 B 组 4 个
        死工具（tool_task_queue/tool_eval/loop_vertical_slice/loop_dispatch_role）
        均不再可导入。"""
        import importlib.util
        for mod in ("tool_quality_gates", "tool_security_scan",
                    "tool_dependency_analysis", "tool_contract_validate",
                    "tool_cost_tracker", "tool_evidence_chain",
                    "scripts.evidence_chain", "scripts.security_scan",
                    "tool_task_queue", "tool_eval",
                    "loop_vertical_slice", "loop_dispatch_role"):
            assert importlib.util.find_spec(mod) is None, f"{mod} 仍存在"


# ═══════════════════════════════════════════════════════════════════════════
# 证据链收敛：loop_core.evidence_chain 为唯一实现（T-0113 legacy 脚本已删）
# ═══════════════════════════════════════════════════════════════════════════

class TestEvidenceChainConvergence:
    @pytest.fixture()
    def chain_root(self, tmp_path: Path) -> Path:
        """fixture 项目根：skills/loop-governance/chain.yaml + 2 个证据节点。"""
        (tmp_path / "skills" / "loop-governance").mkdir(parents=True)
        (tmp_path / ".ai" / "evidence").mkdir(parents=True)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "a.md").write_text("AAA", encoding="utf-8")
        (tmp_path / "docs" / "b.md").write_text("BBB", encoding="utf-8")
        (tmp_path / "skills" / "loop-governance" / "chain.yaml").write_text(
            "chain:\n"
            "  - name: doc-a\n    file: docs/a.md\n    required: true\n"
            "  - name: doc-b\n    file: docs/b.md\n"
            "    upstream: [doc-a]\n",
            encoding="utf-8",
        )
        return tmp_path

    def test_verify_loop_core(self, chain_root):
        """loop_core 唯一实现：verify 输出形态保持（legacy 脚本已删）。"""
        from loop_core.evidence_chain import verify_chain_yaml
        mine = verify_chain_yaml(chain_root, strict=True)
        assert mine["overall"] == "PASS"
        assert {n["name"]: n["status"] for n in mine["nodes"]} == \
            {"doc-a": "PASS", "doc-b": "PASS"}

    def test_verify_missing_node(self, chain_root):
        (chain_root / "docs" / "a.md").unlink()
        from loop_core.evidence_chain import verify_chain_yaml
        assert verify_chain_yaml(chain_root, strict=True)["overall"] == "BLOCKED"
        assert verify_chain_yaml(chain_root, strict=False)["overall"] == "PASS"

    def test_freeze_loop_core(self, chain_root):
        import hashlib
        from loop_core.evidence_chain import freeze_file_yaml
        mine = freeze_file_yaml(chain_root, "docs/a.md")
        assert mine["success"] is True
        record = (chain_root / ".ai" / "evidence" / "frozen" / "a.md.freeze.json")
        assert record.exists()
        data = json.loads(record.read_text(encoding="utf-8"))
        assert data["path"] == "docs/a.md"
        assert data["sha256"] == hashlib.sha256(b"AAA").hexdigest()

    def test_server_dispatch_evidence_verify(self, chain_root):
        import server
        out = server._dispatch("evidence_verify",
                               {"project_root": str(chain_root), "strict": True})
        assert out["overall"] == "PASS"
        assert "nodes" in out  # 收敛后输出为完整校验 dict（旧壳为降级解析）

    def test_server_dispatch_evidence_freeze(self, chain_root):
        import server
        out = server._dispatch("evidence_freeze",
                               {"project_root": str(chain_root), "file": "docs/b.md"})
        assert out["success"] is True


# ═══════════════════════════════════════════════════════════════════════════
# dashboard 四层合并：单一实现 + 输出等价
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardMerge:
    def test_single_implementation(self):
        """status_dashboard 降级为 re-export shim，类本体唯一。"""
        from loop_core.dashboard_views import Dashboard, ProjectStatus
        from loop_core.status_dashboard import Dashboard as ShimDashboard
        from loop_core.status_dashboard import ProjectStatus as ShimStatus
        assert ShimDashboard is Dashboard
        assert ShimStatus is ProjectStatus

    def test_generate_equivalent(self, tmp_path: Path):
        import yaml
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "state.yaml").write_text(
            yaml.safe_dump({"project_name": "Fixture", "current_phase": "S6-delivery",
                            "loop_mode": "FULL"}), encoding="utf-8")
        (tmp_path / ".ai" / "task_graph.yaml").write_text(
            yaml.safe_dump({"tasks": [
                {"id": "T-1", "status": "completed", "phase": "S1-requirements"},
            ]}), encoding="utf-8")
        (tmp_path / ".ai" / "gates.yaml").write_text(
            yaml.safe_dump({"gates": []}), encoding="utf-8")
        from loop_core.dashboard_views import Dashboard
        from loop_core.status_dashboard import Dashboard as ShimDashboard
        d1 = Dashboard(str(tmp_path)).to_dict()
        d2 = ShimDashboard(str(tmp_path)).to_dict()
        for key in ("project_name", "current_phase", "task_stats", "health_indicator"):
            assert d1[key] == d2[key]

    def test_existing_status_dashboard_tests_keep_passing(self):
        """等价实证：既有 test_status_dashboard 全绿（pytest 运行该文件
        在 CI 中覆盖；此处再断言 import 路径健康）。"""
        import loop_core.status_dashboard as mod  # noqa: F401
        assert hasattr(mod, "Dashboard")


# ═══════════════════════════════════════════════════════════════════════════
# T-0109 P1 修复（独立审查 DR-002）：宿主路径注入 —— 候选表无 .zcode
# 字面量（宿主无关回归防护），宿主副本经参数/环境变量注入且优先于仓库源
# ═══════════════════════════════════════════════════════════════════════════

class TestEvidenceChainHostInjection:
    """宿主无关（DR-002）回归防护 + 注入通道行为（T-0105 优先语义保持）。"""

    def test_candidates_host_agnostic(self):
        """候选表为纯仓库相对路径，无 .zcode 字面量（DR-002 回归防护）。"""
        from loop_core.evidence_chain import CHAIN_YAML_CANDIDATES
        assert CHAIN_YAML_CANDIDATES == ("skills/loop-governance/chain.yaml",)
        assert not any(".zcode" in c for c in CHAIN_YAML_CANDIDATES)

    def test_host_candidates_param_injected_priority(self, tmp_path):
        """host_candidates 参数注入的宿主副本优先于仓库源（T-0105 语义保持）。"""
        from loop_core.evidence_chain import load_chain_yaml
        (tmp_path / "skills" / "loop-governance").mkdir(parents=True)
        (tmp_path / "skills" / "loop-governance" / "chain.yaml").write_text(
            "chain:\n  - name: repo-source\n    file: docs/a.md\n",
            encoding="utf-8")
        (tmp_path / "host").mkdir()
        (tmp_path / "host" / "chain.yaml").write_text(
            "chain:\n  - name: host-copy\n    file: docs/b.md\n",
            encoding="utf-8")
        cfg = load_chain_yaml(tmp_path, host_candidates=("host/chain.yaml",))
        assert cfg["chain"][0]["name"] == "host-copy"

    def test_env_injection_config_channel(self, tmp_path, monkeypatch):
        """环境变量为宿主候选的配置通道（注入候选优先于仓库源）。"""
        from loop_core.evidence_chain import (
            ENV_CHAIN_YAML_HOST_CANDIDATE,
            load_chain_yaml,
        )
        (tmp_path / "skills" / "loop-governance").mkdir(parents=True)
        (tmp_path / "skills" / "loop-governance" / "chain.yaml").write_text(
            "chain: []\n", encoding="utf-8")
        (tmp_path / "env-host").mkdir()
        (tmp_path / "env-host" / "chain.yaml").write_text(
            "chain:\n  - name: env-copy\n    file: docs/c.md\n",
            encoding="utf-8")
        monkeypatch.setenv(ENV_CHAIN_YAML_HOST_CANDIDATE, "env-host/chain.yaml")
        cfg = load_chain_yaml(tmp_path)
        assert cfg["chain"][0]["name"] == "env-copy"

    def test_injected_missing_falls_back_to_repo_source(self, tmp_path):
        """注入候选缺失 → 仓库源回退（原 .zcode 缺失回退语义保持）。"""
        from loop_core.evidence_chain import load_chain_yaml
        (tmp_path / "skills" / "loop-governance").mkdir(parents=True)
        (tmp_path / "skills" / "loop-governance" / "chain.yaml").write_text(
            "chain:\n  - name: repo-source\n    file: docs/a.md\n",
            encoding="utf-8")
        cfg = load_chain_yaml(tmp_path, host_candidates=("no-such-host/chain.yaml",))
        assert cfg["chain"][0]["name"] == "repo-source"


# ═══════════════════════════════════════════════════════════════════════════
# AC-05: enforcement 白名单与工具变更同步
# ═══════════════════════════════════════════════════════════════════════════

def _extract_governance_tool_dirs() -> list[str]:
    """AST 提取 hooks/scripts/loop_enforcement.py 的 GOVERNANCE_TOOL_DIRS
    常量表（不执行 hook 代码，避免引入执行环境依赖）。"""
    source = (PROJECT_ROOT / "hooks" / "scripts" / "loop_enforcement.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        # 常量声明形态：GOVERNANCE_TOOL_DIRS: tuple[str, ...] = ( ... )
        target_nodes: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            target_nodes = node.targets
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_nodes = [node.target]
        for target in target_nodes:
            if isinstance(target, ast.Name) and target.id == "GOVERNANCE_TOOL_DIRS":
                value = node.value if isinstance(node, ast.Assign) else node.value
                assert value is not None and isinstance(value, ast.Tuple), \
                    "GOVERNANCE_TOOL_DIRS 必须仍是 tuple 字面量"
                return [ast.literal_eval(elt) for elt in value.elts]
    raise AssertionError("GOVERNANCE_TOOL_DIRS 未找到")


class TestWhitelistConsistency:
    def test_every_registered_tool_covered_by_whitelist(self):
        """注册表 26 工具模块路径全部落在白名单目录内（目录级覆盖，
        工具变更无需逐文件同步）。"""
        dirs = _extract_governance_tool_dirs()
        assert "tools/" in dirs
        for name in all_tool_names():
            rel = f"tools/{name}.py"
            assert any(rel.startswith(d) for d in dirs), f"{rel} 不在白名单内"

    def test_whitelist_dirs_stable(self):
        """白名单常量表仍为既有 6 目录（T-0109 仅注释同步，功能零改动）。"""
        dirs = _extract_governance_tool_dirs()
        assert dirs == [".zcode/tools/", ".ai/checkers/", ".ai/guards/",
                        "scripts/", "hooks/", "tools/"]

    def test_hooks_zero_changes(self):
        """hooks/ 仅允许白名单注释级改动（T-0113/T-0114 硬约束 hooks/ 零改动；
        T-0119 用户 gate 批准 loop_enforcement_constants.py 注释级清理——
        死引用注释清除。工作树 hooks diff 必须为空或仅该文件，且为注释级）。"""
        import subprocess as sp
        out = sp.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only", "HEAD", "--", "hooks/"],
            capture_output=True, text=True, timeout=30,
        )
        assert out.returncode == 0, out.stderr
        changed = [p for p in out.stdout.splitlines() if p.strip()]
        allowed = {"hooks/scripts/loop_enforcement_constants.py"}
        disallowed = [p for p in changed if p not in allowed]
        assert disallowed == [], f"hooks/ 仅允许白名单文件改动: {disallowed}"
        if changed:
            # T-0119：白名单文件改动须为注释级（新增行必须为注释或空行）
            diff = sp.run(
                ["git", "-C", str(PROJECT_ROOT), "diff", "HEAD", "--",
                 "hooks/scripts/loop_enforcement_constants.py"],
                capture_output=True, text=True, timeout=30,
            )
            added_lines = [ln for ln in diff.stdout.splitlines()
                           if ln.startswith("+") and not ln.startswith("+++")]
            assert all(ln.lstrip("+").lstrip().startswith("#") or not ln.lstrip("+").strip()
                       for ln in added_lines), f"白名单文件仅允许注释级改动: {added_lines}"
