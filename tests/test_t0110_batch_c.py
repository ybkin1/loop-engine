"""T-0110 批 C — hooks/scripts/loop_enforcement.py 行为等价拆分验收测试。

覆盖（任务卡批 C 硬门槛 1/2/4/5 + AC-03）：
1. golden 逐字节等价：复用 t0110_c_golden 捕获器（hook 入口判定矩阵
   51 场景子进程实跑 + 关键函数直调 204 项 + dir/公开面快照），运行时
   重放与 golden-c-before.json（拆分前捕获）sha256 逐字节对比；
2. re-export 完整性：dir() 全量 == 拆分前基线（104 名含私有名）、
   import * 公开面一致、壳绑定即新模块定义对象（对象同一性）、
   常量表接线（EXIT_PASS/EXIT_BLOCK/_REEXEC_MAX/治理白名单）；
3. 自愈 re-exec 实测（AC-03）：构造"缓存陈旧 + 本地新代码"场景 →
   改本地常量表 → 触发 re-exec 恰好一次 → 最终判定与新代码一致
   （re-exec 前后判定一致）；无修改基线对照（不触发、按旧代码判定）；
4. 循环导入静态防线（叶子模块零反向引用壳）+ AC-01 grep 零散落
   （5 个 hook 文件零 timeout= 字面量）+ GOVERNANCE_TOOL_DIRS 双登记
   一致性（T-0109 AC-05 AST 门禁兼容）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "hooks" / "scripts"
PYTHON = sys.executable
GOLDEN_BEFORE = REPO_ROOT / ".ai" / "evidence" / "T-0110" / "golden" / "golden-c-before.json"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPTS))

import gate_evidence_checks as GEC  # noqa: E402, N812
import loop_command_utils as LCU  # noqa: E402, N812
import loop_contract_parser as LCP  # noqa: E402, N812
import loop_enforcement as LE  # noqa: E402, N812
import loop_enforcement_constants as HKC  # noqa: E402, N812
from t0110_c_golden import capture_all, dump_json  # noqa: E402


def _golden_text() -> str:
    """运行时重放完整 golden 语料（与生成器同一捕获器）。"""
    with tempfile.TemporaryDirectory() as tmp:
        payload = capture_all(Path(tmp))
    return dump_json(payload)


# ═══════════════════════════════════════════════════════════════════════
# 1. golden 逐字节等价（硬门槛 1：拆分前后 stdout/exit code 逐字节一致）
# ═══════════════════════════════════════════════════════════════════════


class TestGoldenByteEquivalence:
    def test_golden_replay_byte_identical_to_baseline(self):
        """运行时重放捕获 == 拆分前 golden 快照（统一换行后逐字节一致）。

        注：Windows 上 Path.write_text 落盘为 CRLF，而内存中 dump_json 输出
        为 LF —— 两侧统一经 read_text（universal newlines）归一化后逐字节
        对比；golden 生成器与测试使用同一捕获器与 dump_json。
        """
        assert GOLDEN_BEFORE.is_file(), f"golden 基线缺失: {GOLDEN_BEFORE}"
        expected = GOLDEN_BEFORE.read_text(encoding="utf-8")
        actual = _golden_text()
        assert hashlib.sha256(actual.encode("utf-8")).hexdigest() == \
            hashlib.sha256(expected.encode("utf-8")).hexdigest()
        assert actual == expected

    def test_golden_baseline_covers_full_behavior_surface(self):
        """golden 语料面完整性抽查：关键场景/函数必须在基线内。"""
        golden = json.loads(GOLDEN_BEFORE.read_text(encoding="utf-8"))
        matrix = golden["hook_entry_matrix"]
        for name in (
            "full_task_in_scope_write_passes",
            "full_task_out_of_scope_write_blocks",
            "write_outside_project_root_blocks",
            "s4_no_baselines_blocks_c1c2c6",
            "s5_quality_with_security_passes",
            "s6_slo_sources_missing_blocks",
            "mcp_not_in_allowlist_blocks",
            "mcp_in_allowlist_with_identity",
            "self_review_evidence_blocks",
            "runtime_projection_missing_setup_incomplete",
            "governance_tool_compound_main_session_passes",
            "c11_second_write_blocks_limit",
        ):
            assert name in matrix, f"矩阵缺少场景 {name}"
        direct = golden["direct_calls"]
        for name in (
            "is_governance_tool_command_exempt_python_zcode_tools",
            "is_governance_tool_command_not_python_c",
            "check_diff_scope_out_of_scope_files_blocks",
            "check_diff_scope_git_timeout_not_verified",
            "load_task_contract_inline",
            "build_hard_constraints_context",
            "trace_review_evidence_isolation_self_review_blocks",
            "phase_gate_s6_slo_disabled",
        ):
            assert name in direct, f"直调缺少 {name}"


# ═══════════════════════════════════════════════════════════════════════
# 2. re-export 完整性（硬门槛 4：dir() 全量 == 基线，含私有名 +
#    import * 公开面一致）
# ═══════════════════════════════════════════════════════════════════════


class TestReexportCompleteness:
    @pytest.fixture(scope="class")
    def golden(self):
        return json.loads(GOLDEN_BEFORE.read_text(encoding="utf-8"))

    def test_dir_snapshot_equals_baseline(self, golden):
        """dir() 全量 == 拆分前基线（104 名，含私有名，零缺失零新增）。"""
        baseline = golden["dir_snapshot"]
        now = sorted(dir(LE))
        assert now == baseline

    def test_star_import_public_face_identical(self, golden):
        """import * 公开面 == 基线公开名（55 名）。"""
        ns: dict = {}
        exec("from loop_enforcement import *", ns)  # noqa: S102
        public = sorted(k for k in ns if not k.startswith("_"))
        baseline_public = sorted(
            n for n in golden["dir_snapshot"] if not n.startswith("_"))
        assert public == baseline_public

    def test_shell_bindings_are_new_module_objects(self):
        """壳绑定即新模块定义对象（对象同一性 12 项）。"""
        assert LE.load_task_contract is LCP.load_task_contract
        assert LE._task_mcp_allowed_tools is LCP._task_mcp_allowed_tools
        assert LE._read_task_max_files is LCP._read_task_max_files
        assert LE._front_matter_parser is LCP._front_matter_parser
        assert LE._parse_task_front_matter_legacy is LCP._parse_task_front_matter_legacy
        assert LE.check_diff_scope is LCU.check_diff_scope
        assert LE.is_in_task_scope is LCU.is_in_task_scope
        assert LE._split_command_segments is LCU._split_command_segments
        assert LE._command_references_outside is LCU._command_references_outside
        assert LE.check_phase_gate_enforcement is GEC.check_phase_gate_enforcement
        assert LE.check_quality_gate_evidence is GEC.check_quality_gate_evidence
        assert LE.trace_review_evidence_isolation is GEC.trace_review_evidence_isolation

    def test_constants_wiring_m1_reexec(self):
        """批 A 常量表接线：M-1 返回码 / 自愈上限 / 治理白名单。"""
        assert LE.EXIT_PASS is HKC.EXIT_PASS == 0
        assert LE.EXIT_BLOCK is HKC.EXIT_BLOCK == 2
        assert LE._REEXEC_MAX == HKC.REEXEC_MAX == 1
        assert LE.GOVERNANCE_EXEMPT is HKC.GOVERNANCE_EXEMPT
        assert LE.MINIMAL_METADATA_READ is HKC.MINIMAL_METADATA_READ
        assert LE.MAIN_THREAD_ALLOWED is HKC.MAIN_THREAD_ALLOWED

    def test_governance_tool_dirs_dual_registration_consistent(self):
        """GOVERNANCE_TOOL_DIRS 双登记（T-0109 AC-05 AST 门禁要求壳内保留
        tuple 字面量）：壳字面量 == 常量表登记值。"""
        assert LE.GOVERNANCE_TOOL_DIRS == HKC.GOVERNANCE_TOOL_DIRS
        assert list(LE.GOVERNANCE_TOOL_DIRS) == [
            ".zcode/tools/", ".ai/checkers/", ".ai/guards/",
            "scripts/", "hooks/", "tools/",
        ]

    def test_governance_tool_dirs_ast_literal_kept(self):
        """壳源文件内 GOVERNANCE_TOOL_DIRS 仍是 tuple 字面量（T-0109
        _extract_governance_tool_dirs 的 AST 断言前提，兼容门禁）。"""
        import ast
        source = (SCRIPTS / "loop_enforcement.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in tree.body:
            targets = (node.targets if isinstance(node, ast.Assign) else
                       ([node.target] if isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name) else []))
            for t in targets:
                if isinstance(t, ast.Name) and t.id == "GOVERNANCE_TOOL_DIRS":
                    assert isinstance(node.value, ast.Tuple), \
                        "GOVERNANCE_TOOL_DIRS 必须仍是 tuple 字面量"
                    assert [ast.literal_eval(e) for e in node.value.elts] == [
                        ".zcode/tools/", ".ai/checkers/", ".ai/guards/",
                        "scripts/", "hooks/", "tools/",
                    ]
                    found = True
        assert found, "壳内未找到 GOVERNANCE_TOOL_DIRS 字面量"


# ═══════════════════════════════════════════════════════════════════════
# 3. 自愈 re-exec 实测（AC-03：re-exec 一次、判定一致）
# ═══════════════════════════════════════════════════════════════════════

_HOOK_FILES = [
    "loop_enforcement.py", "hook_common.py", "_hook_bash.py",
    "_hook_state.py", "_hook_path.py", "_hook_config.py", "_hook_sync.py",
    "loop_contract_parser.py", "loop_command_utils.py",
    "gate_evidence_checks.py", "loop_enforcement_constants.py",
]

_FIXTURE_STATE = """\
schema_version: 1
project_name: self-heal-fixture
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

_FIXTURE_TASK = """\
# Task T-0001
allowed_paths:
- src/
"""

_FIXTURE_GATES = """\
schema_version: 1
gates:
- id: G-T-0001-REQUIREMENTS
  task_id: T-0001
  gate_type: requirements
  status: approved
- id: G-T-0001-ARCHITECTURE
  task_id: T-0001
  gate_type: architecture
  status: approved
"""

_FIXTURE_CONFIG = """\
# loop-governance behavior config (synthetic fixture)
version: 1
gate_guard:
  enabled: true
  fail_on_state_error: closed
"""


def _make_self_heal_fixture(base: Path) -> Path:
    """受治理 fixture 项目（含本地 hooks/scripts 副本 —— auto_sync 的
    项目侧真相源）。"""
    root = base / "project"
    (root / ".ai" / "tasks").mkdir(parents=True)
    (root / ".ai" / "evidence" / "T-0001").mkdir(parents=True)
    (root / ".zcode" / "skills" / "loop-governance").mkdir(parents=True)
    (root / "hooks" / "scripts").mkdir(parents=True)
    (root / ".ai" / "state.yaml").write_text(_FIXTURE_STATE, encoding="utf-8")
    (root / ".ai" / "tasks" / "T-0001.md").write_text(_FIXTURE_TASK, encoding="utf-8")
    (root / ".ai" / "gates.yaml").write_text(_FIXTURE_GATES, encoding="utf-8")
    (root / ".zcode" / "skills" / "loop-governance" / "config.yaml").write_text(
        _FIXTURE_CONFIG, encoding="utf-8")
    (root / ".ai" / "evidence" / "T-0001" / "review-evidence.json").write_text(
        '{"task_id": "T-0001", "role": "independent-reviewer", '
        '"verdict": "PASS", "findings": [], '
        '"reviewer_session_id": "s-r", "developer_session_id": "s-d"}',
        encoding="utf-8")
    for name in _HOOK_FILES:
        shutil.copy(str(SCRIPTS / name), str(root / "hooks" / "scripts" / name))
    return root


def _run_self_heal_hook(script: Path, root: Path, hook_input: dict):
    """子进程运行 hook 副本（模拟插件缓存侧；真实主会话无 PYTEST_CURRENT_TEST）。"""
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ZCODE_PROJECT_DIR"] = str(root)
    return subprocess.run(
        [PYTHON, str(script)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


class TestSelfHealReexec:
    """AC-03：自愈 re-exec 一次、判定一致（拆分后实测）。"""

    def _scenario(self, modify_local: bool):
        base = Path(tempfile.mkdtemp())
        cache = base / "cache" / "hooks" / "scripts"
        cache.mkdir(parents=True)
        for name in _HOOK_FILES:
            shutil.copy(str(SCRIPTS / name), str(cache / name))
        root = _make_self_heal_fixture(base)
        if modify_local:
            # 本地新代码：把 extra/ 加入 GOVERNANCE_EXEMPT（仅改 fixture 副本，
            # 仓库零改动）。缓存侧仍是旧代码 → 首次运行必然触发自愈 re-exec。
            constants = root / "hooks" / "scripts" / "loop_enforcement_constants.py"
            text = constants.read_text(encoding="utf-8")
            assert '".zcode/config.json",\n]' in text
            constants.write_text(
                text.replace('".zcode/config.json",\n]',
                             '".zcode/config.json",\n    "extra/",\n]'),
                encoding="utf-8")
        return cache / "loop_enforcement.py", root

    def test_self_heal_reexec_once_and_judgment_matches_fresh_code(self):
        """缓存旧代码（extra/ 不豁免）+ 本地新代码（extra/ 豁免）：
        - 首次调用触发 re-exec 恰好一次；
        - 最终判定 == 新代码判定（rc 0，而非旧代码的 SETUP_INCOMPLETE rc 2）；
        - 同步后缓存 == 本地（新代码已就位）。
        """
        script, root = self._scenario(modify_local=True)

        # 旧代码对 extra/ 的判定：未豁免 → 无 projection → SETUP_INCOMPLETE BLOCK
        # 新代码对 extra/ 的判定：GOVERNANCE_EXEMPT → PASS
        r1 = _run_self_heal_hook(
            script, root,
            {"tool_name": "Write", "tool_input": {
                "file_path": str(root / "extra" / "x.txt")}})
        assert r1.returncode == 0, f"stderr: {r1.stderr[-800:]}"
        assert r1.stderr.count("re-executing with fresh code") == 1, \
            f"应恰好 re-exec 一次: {r1.stderr}"
        # 同步后缓存已是最新代码（含 extra/ 豁免）
        assert "extra/" in (script.parent / "loop_enforcement_constants.py").read_text(
            encoding="utf-8")

        # 第二次调用：文件无变化 → 不触发 re-exec；范围外写入仍 BLOCK
        r2 = _run_self_heal_hook(
            script, root,
            {"tool_name": "Write", "tool_input": {
                "file_path": str(root / "docs" / "y.txt")}})
        assert r2.returncode == 2, f"stderr: {r2.stderr[-800:]}"
        assert "re-executing with fresh code" not in r2.stderr

        # 第三次调用：新代码已加载 → 直接放行豁免路径，不再 re-exec
        r3 = _run_self_heal_hook(
            script, root,
            {"tool_name": "Write", "tool_input": {
                "file_path": str(root / "extra" / "z.txt")}})
        assert r3.returncode == 0, f"stderr: {r3.stderr[-800:]}"
        assert "re-executing with fresh code" not in r3.stderr

    def test_self_heal_baseline_no_modification_blocks_without_reexec(self):
        """对照：本地 == 缓存（无修改）→ 不触发 re-exec，extra/ 按旧代码
        BLOCK（SETUP_INCOMPLETE，fail-closed 保持）。"""
        script, root = self._scenario(modify_local=False)
        r = _run_self_heal_hook(
            script, root,
            {"tool_name": "Write", "tool_input": {
                "file_path": str(root / "extra" / "x.txt")}})
        assert r.returncode == 2, f"stderr: {r.stderr[-800:]}"
        assert "re-executing with fresh code" not in r.stderr
        assert "SETUP_INCOMPLETE" in r.stderr


# ═══════════════════════════════════════════════════════════════════════
# 4. 循环导入静态防线 + AC-01 grep 零散落
# ═══════════════════════════════════════════════════════════════════════

_SPLIT_MODULE_FILES = (
    "loop_contract_parser.py",
    "loop_command_utils.py",
    "gate_evidence_checks.py",
    "loop_enforcement_constants.py",
)


class TestDependencyDagAndScatter:
    def test_leaf_modules_never_import_shell(self):
        """依赖图叶子方向：4 个拆分模块零反向引用壳（循环导入静态防线）。"""
        for name in _SPLIT_MODULE_FILES:
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            imports = re.findall(
                r"^\s*(?:import loop_enforcement\b|from loop_enforcement\b)",
                source, re.M)
            assert imports == [], f"{name} 反向引用壳: {imports}"

    def test_no_timeout_literals_in_hook_files(self):
        """AC-01 接线后零新散落：4 个 hook 代码文件无 timeout= 字面量
        （常量表文件为超时族注册处，其注释提及属登记记录——批 A 同口径）。"""
        for name in ("loop_enforcement.py", "loop_contract_parser.py",
                     "loop_command_utils.py", "gate_evidence_checks.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            assert re.findall(r"timeout=\d+", source) == [], \
                f"{name}: 残留 timeout= 字面量"
        # 常量表内仅注释提及（M-3/M-4 登记记录），无代码赋值散落
        constants = (SCRIPTS / "loop_enforcement_constants.py").read_text(
            encoding="utf-8")
        for m in re.finditer(r"timeout=\d+", constants):
            line = constants[: m.start()].rfind("\n")
            assert "#" in constants[line + 1: m.start()], \
                "常量表内 timeout= 仅允许出现在注释（登记记录）"

    def test_new_modules_importable_standalone(self):
        """4 个拆分模块可独立导入（无壳依赖）。"""
        for name in _SPLIT_MODULE_FILES:
            module_name = name[:-3]
            __import__(module_name)

    def test_self_heal_snapshot_covers_split_modules(self):
        """自愈扫描集已覆盖 4 个拆分模块（改任一判定文件都能触发 re-exec）。"""
        source = (SCRIPTS / "loop_enforcement.py").read_text(encoding="utf-8")
        for name in _SPLIT_MODULE_FILES:
            assert f'"{name}"' in source, f"扫描集缺少 {name}"
