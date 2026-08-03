"""T-0110 批 B-1：governance_metrics / intent_router 行为等价拆分验收测试。

覆盖（任务卡 AC-02 / 拆分要求）：
1. **golden 逐字节等价**：重放固定语料（tests/t0110_b1_golden.py 捕获函数），
   与拆分前基线 `.ai/evidence/T-0110/golden/golden-before.json` 逐字节对比
   （governance_metrics 全量：加载器/度量函数/SLO 配置与评估/budget/DORA/
   报告 to_dict+markdown；intent_router 全量：词表/analyze×语料×上下文/
   should_escalate/route/切分与切换/U5 路由主流程）。
2. **re-export 完整性**：dir() 全量快照与基线一致（含私有名）；公开符号
   （import * 面）集合一致；壳与新模块对象同一性断言。
3. **循环导入规避**：新模块源码零反向引用壳；叶子→壳依赖顺序静态断言。
4. **内嵌抽查**：关键数值/输出格式代表性断言（自包含，不依赖 golden 文件）。
"""
from __future__ import annotations

import importlib
import inspect
import json
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from t0110_b1_golden import (  # noqa: E402
    capture_governance_metrics_golden,
    capture_intent_router_golden,
    dump_json,
)

GOLDEN_PATH = _REPO_ROOT / ".ai" / "evidence" / "T-0110" / "golden" / "golden-before.json"


def _load_golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.fail(
            f"golden 基线缺失: {GOLDEN_PATH}（先运行 "
            ".ai/evidence/T-0110/golden/generate_golden.py golden-before.json）"
        )
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════
# 1. golden 逐字节等价
# ═══════════════════════════════════════════════════════════════════════


def test_golden_metrics_byte_identical():
    """governance_metrics 全量 golden 与拆分前基线逐字节一致。"""
    golden = _load_golden()
    with tempfile.TemporaryDirectory() as tmp:
        captured = capture_governance_metrics_golden(Path(tmp))
    assert dump_json(captured) == dump_json(golden["governance_metrics"])


def test_golden_intent_byte_identical():
    """intent_router 全量 golden 与拆分前基线逐字节一致。"""
    golden = _load_golden()
    captured = capture_intent_router_golden()
    assert dump_json(captured) == dump_json(golden["intent_router"])


# ═══════════════════════════════════════════════════════════════════════
# 2. re-export 完整性（dir() 全量 + import * 公开面 + 对象同一性）
# ═══════════════════════════════════════════════════════════════════════


def _public_names(names: list[str]) -> list[str]:
    return sorted(n for n in names if not n.startswith("_"))


def test_reexport_surface_governance_metrics():
    """governance_metrics 壳 dir() 与拆分前基线一致；import * 公开面一致。"""
    import loop_core.governance_metrics as gm

    golden = _load_golden()
    baseline = golden["dir_snapshots"]["loop_core.governance_metrics"]
    current = sorted(dir(gm))
    assert current == baseline, (
        f"dir() 漂移: 拆分前 {len(baseline)} 名，拆分后 {len(current)} 名。"
        f"丢失: {sorted(set(baseline) - set(current))}  "
        f"新增: {sorted(set(current) - set(baseline))}"
    )
    # import * 公开面（与拆分前公开符号集合一致）
    assert _public_names(current) == _public_names(baseline)


def test_reexport_surface_intent_router():
    """intent_router 壳 dir() 与拆分前基线一致；import * 公开面一致。"""
    import loop_core.intent_router as ir

    golden = _load_golden()
    baseline = golden["dir_snapshots"]["loop_core.intent_router"]
    current = sorted(dir(ir))
    assert current == baseline, (
        f"dir() 漂移: 拆分前 {len(baseline)} 名，拆分后 {len(current)} 名。"
        f"丢失: {sorted(set(baseline) - set(current))}  "
        f"新增: {sorted(set(current) - set(baseline))}"
    )
    assert _public_names(current) == _public_names(baseline)


def test_reexport_object_identity_metrics():
    """壳 re-export 的对象与新模块定义对象同一（非拷贝）。"""
    import loop_core.dora_metrics as dm
    import loop_core.governance_aggregations as agg
    import loop_core.governance_loaders as ld
    import loop_core.governance_metrics as gm
    import loop_core.slo_evaluator as se

    assert gm.GateMetric is agg.GateMetric
    assert gm.SliContext is agg.SliContext
    assert gm._parse_dt is agg._parse_dt
    assert gm.load_gates is ld.load_gates
    assert gm.load_guard_events is ld.load_guard_events
    assert gm.DataSourceUnavailableError is ld.DataSourceUnavailableError
    assert gm.evaluate_sli is se.evaluate_sli
    assert gm.load_slo_config is se.load_slo_config
    assert gm.NOT_AVAILABLE == se.NOT_AVAILABLE
    assert gm.build_dora_metrics is dm.build_dora_metrics
    assert gm.git_commit is dm.git_commit


def test_reexport_object_identity_intent():
    """intent_router 壳 re-export 的对象与新模块定义对象同一（非拷贝）。"""
    import loop_core.intent_detection as det
    import loop_core.intent_keywords as kw
    import loop_core.intent_router as ir
    import loop_core.intent_split as sp

    assert ir.DOMAIN_KEYWORDS is kw.DOMAIN_KEYWORDS
    assert ir.SCALE_INDICATORS is kw.SCALE_INDICATORS
    assert ir._NEGATION_PATTERNS is kw._NEGATION_PATTERNS
    assert ir._detect_domains is det._detect_domains
    assert ir._extract_risk_factors is det._extract_risk_factors
    assert ir._set_if_match is det._set_if_match
    assert ir.split_intents is sp.split_intents
    assert ir._INTENT_SPLIT_RE is sp._INTENT_SPLIT_RE
    assert ir.detect_intent_switch is sp.detect_intent_switch
    assert ir._MAX_TASK_FRAMES == sp._MAX_TASK_FRAMES


def test_star_import_works():
    """from loop_core.X import * 可执行且公开面与 dir() 非下划线名一致。"""
    import loop_core.governance_metrics as gm
    import loop_core.intent_router as ir

    ns = {}
    exec("from loop_core.governance_metrics import *", ns)  # noqa: S102 — 验收断言
    assert {k for k in ns if not k.startswith("_")} == {
        n for n in dir(gm) if not n.startswith("_")
    }
    ns2 = {}
    exec("from loop_core.intent_router import *", ns2)  # noqa: S102 — 验收断言
    assert {k for k in ns2 if not k.startswith("_")} == {
        n for n in dir(ir) if not n.startswith("_")
    }


# ═══════════════════════════════════════════════════════════════════════
# 3. 循环导入规避（叶子先拆；新模块零反向引用壳）
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("module_name", [
    "loop_core.governance_aggregations",
    "loop_core.governance_loaders",
    "loop_core.slo_evaluator",
    "loop_core.dora_metrics",
])
def test_metrics_leaves_do_not_import_shell(module_name):
    """governance_metrics 新模块源码零反向引用壳（循环导入防线）。"""
    mod = importlib.import_module(module_name)
    src = inspect.getsource(mod)
    assert "from loop_core.governance_metrics import" not in src
    assert "import loop_core.governance_metrics" not in src


@pytest.mark.parametrize("module_name", [
    "loop_core.intent_keywords",
    "loop_core.intent_detection",
    "loop_core.intent_split",
])
def test_intent_leaves_do_not_import_shell(module_name):
    """intent_router 新模块源码零反向引用壳（循环导入防线）。"""
    import re as _re
    mod = importlib.import_module(module_name)
    src = inspect.getsource(mod)
    assert not _re.search(
        r"^\s*(?:from\s+loop_core\.intent_router\s+import|import\s+loop_core\.intent_router)\b",
        src, _re.MULTILINE)


def test_dependency_dag_order():
    """叶子→壳依赖顺序：aggregations 无 loop_core 内部依赖；
    loaders 仅依赖 aggregations；slo_evaluator 依赖 loaders+aggregations；
    dora_metrics 依赖 aggregations+slo_evaluator。"""
    import loop_core.dora_metrics as dm
    import loop_core.governance_aggregations as agg
    import loop_core.governance_loaders as ld
    import loop_core.slo_evaluator as se

    for mod in (agg, ld, se, dm):
        importlib.import_module(mod.__name__)  # 已成功导入即无循环
    agg_src = inspect.getsource(agg)
    assert "from loop_core.governance" not in agg_src  # 叶子：零内部依赖
    ld_src = inspect.getsource(ld)
    assert "from loop_core.governance_aggregations import" in ld_src
    assert "from loop_core.slo_evaluator import" not in ld_src
    se_src = inspect.getsource(se)
    assert "from loop_core.governance_aggregations import" in se_src
    assert "from loop_core.governance_loaders import" in se_src
    dm_src = inspect.getsource(dm)
    assert "from loop_core.slo_evaluator import" in dm_src


# ═══════════════════════════════════════════════════════════════════════
# 4. 内嵌抽查（自包含代表性断言）
# ═══════════════════════════════════════════════════════════════════════


def test_spot_check_metrics():
    """代表性数值/格式抽查（与 golden 同源但自包含）。"""
    from loop_core.governance_metrics import (
        BUDGET_CONSUMING,
        NOT_AVAILABLE,
        build_report,
        classify_gate_phase,
        render_markdown,
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        from t0110_b1_golden import write_metrics_fixture
        write_metrics_fixture(root)
        assert classify_gate_phase("G-T-0001-REQUIREMENTS") == "S1-requirements"
        assert classify_gate_phase("G-T-0006-UNMAPPED") is None
        report = build_report(root)
        assert report.status == NOT_AVAILABLE or report.status == "NOT_VERIFIED"
        assert report.budget["status"] == BUDGET_CONSUMING
        assert report.to_dict()["schema_version"] == 1
        md = render_markdown(report)
        assert md.startswith("# Loop-DORA Metrics Report")
        assert "## Error budget" in md and "## SLI / SLO evaluation" in md


def test_spot_check_intent():
    """代表性路由决策抽查（与 golden 同源但自包含）。"""
    from loop_core.intent_router import (
        IntentRouter,
        analyse_intent,
        route_user_input,
        split_intents,
    )
    from loop_core.router import LoopMode

    router = IntentRouter()
    low = router.analyze("Fix a typo in the readme")
    assert low.recommended_mode == LoopMode.LIGHTWEIGHT
    high = router.analyze("Build a payment gateway with postgresql")
    assert high.recommended_mode == LoopMode.FULL
    assert "has_payments" in high.risk_factors and high.risk_factors["has_payments"]
    assert split_intents("Build a web app; then add payment") == [
        "Build a web app", "add payment"
    ]
    assert split_intents("登录之后修改设置") == ["登录之后修改设置"]
    result = route_user_input("Build a web app with react", None)
    assert not result.degraded and result.analysis is not None
    brief = analyse_intent("set up a data pipeline")
    assert brief.domains and brief.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    degraded = route_user_input(123)
    assert degraded.degraded and degraded.task_frames == []
