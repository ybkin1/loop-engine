"""T-0110 批 B-2：human_review_packet / context_loader 行为等价拆分验收测试。

覆盖（任务卡 AC-02 / 拆分要求）：
1. **golden 逐字节等价**：重放固定语料（tests/t0110_b2_golden.py 捕获函数），
   与拆分前基线 `.ai/evidence/T-0110/golden/golden-b2-before.json` 逐字节对比
   （human_review_packet 全量：模型/序列化+失败路径/build_resume_payload 成功+
   fail-closed 11 例/resume_from_payload 成功+drift 9 例/渲染全文/builder 三路；
   context_loader 全量：常量与正则族/摘要级别辅助/summarize_text/estimate_tokens/
   CitationResolver 9 例+自定义 roots/repair 3 例（含 T-0095 子串守卫）/
   ContextCompressor 8 例/load_role_context 3 级+3 失败/D3 记忆注入 6 例/
   文档索引/load_for_role 3 例/节选择 7 例/front-matter+路由缓存）。
2. **re-export 完整性**：dir() 全量快照与基线一致（含私有名）；import * 公开面
   一致；壳与新模块对象同一性断言；_ROUTING_CACHE 同一 dict 对象。
3. **循环导入规避**：新模块源码零反向引用壳（TYPE_CHECKING 仅类型检查）。
4. **include_memories 默认 False 保持**（T-0104 硬约束）：kwdefaults 断言 +
   默认加载不读知识库（损坏存储默认关闭不报错）。
5. **内嵌抽查**：代表性输出/数值断言（自包含，不依赖 golden 文件）。
"""
from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from t0110_b1_golden import dump_json  # noqa: E402
from t0110_b2_golden import (  # noqa: E402
    capture_context_loader_golden,
    capture_human_review_packet_golden,
)

GOLDEN_PATH = _REPO_ROOT / ".ai" / "evidence" / "T-0110" / "golden" / "golden-b2-before.json"


def _load_golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.fail(
            f"golden 基线缺失: {GOLDEN_PATH}（先运行 "
            ".ai/evidence/T-0110/golden/generate_golden_b2.py）"
        )
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════
# 1. golden 逐字节等价
# ═══════════════════════════════════════════════════════════════════════


def test_golden_human_review_packet_byte_identical():
    """human_review_packet 全量 golden 与拆分前基线逐字节一致。"""
    golden = _load_golden()
    with tempfile.TemporaryDirectory() as tmp:
        captured = capture_human_review_packet_golden(Path(tmp))
    assert dump_json(captured) == dump_json(golden["human_review_packet"])


def test_golden_context_loader_byte_identical():
    """context_loader 全量 golden 与拆分前基线逐字节一致。"""
    golden = _load_golden()
    with tempfile.TemporaryDirectory() as tmp:
        captured = capture_context_loader_golden(Path(tmp))
    assert dump_json(captured) == dump_json(golden["context_loader"])


# ═══════════════════════════════════════════════════════════════════════
# 2. re-export 完整性（dir() 全量 + import * 公开面 + 对象同一性）
# ═══════════════════════════════════════════════════════════════════════


def _public_names(names: list[str]) -> list[str]:
    return sorted(n for n in names if not n.startswith("_"))


def test_reexport_surface_human_review_packet():
    """human_review_packet 壳 dir() 与拆分前基线一致；import * 公开面一致。"""
    import loop_core.human_review_packet as hrp

    golden = _load_golden()
    baseline = golden["dir_snapshots"]["loop_core.human_review_packet"]
    current = sorted(dir(hrp))
    assert current == baseline, (
        f"dir() 漂移: 拆分前 {len(baseline)} 名，拆分后 {len(current)} 名。"
        f"丢失: {sorted(set(baseline) - set(current))}  "
        f"新增: {sorted(set(current) - set(baseline))}"
    )
    assert _public_names(current) == _public_names(baseline)


def test_reexport_surface_context_loader():
    """context_loader 壳 dir() 与拆分前基线一致；import * 公开面一致。"""
    import loop_core.context_loader as cl

    golden = _load_golden()
    baseline = golden["dir_snapshots"]["loop_core.context_loader"]
    current = sorted(dir(cl))
    assert current == baseline, (
        f"dir() 漂移: 拆分前 {len(baseline)} 名，拆分后 {len(current)} 名。"
        f"丢失: {sorted(set(baseline) - set(current))}  "
        f"新增: {sorted(set(current) - set(baseline))}"
    )
    assert _public_names(current) == _public_names(baseline)


def test_reexport_object_identity_human_review_packet():
    """壳 re-export 的对象与新模块定义对象同一（非拷贝）。"""
    import loop_core.human_review_packet as hrp
    import loop_core.resume_payload as rp
    import loop_core.review_models as rm
    import loop_core.review_renderer as rr

    assert hrp.PacketType is rm.PacketType
    assert hrp.KeyChoice is rm.KeyChoice
    assert hrp.ResumeSnapshot is rm.ResumeSnapshot
    assert hrp.ResumePayload is rm.ResumePayload
    assert hrp.ResumePayloadError is rm.ResumePayloadError
    assert hrp.StateDriftError is rm.StateDriftError
    assert hrp.RESUME_PAYLOAD_SCHEMA == rm.RESUME_PAYLOAD_SCHEMA
    assert hrp.build_resume_payload is rp.build_resume_payload
    assert hrp.resume_from_payload is rp.resume_from_payload
    assert hrp._load_authoritative_yaml is rp._load_authoritative_yaml
    assert hrp._task_recovery_record is rp._task_recovery_record
    assert hrp._phase_label is rr._phase_label
    assert hrp._format_ts is rr._format_ts


def test_reexport_object_identity_context_loader():
    """壳 re-export 的对象与新模块定义对象同一（非拷贝）。"""
    import loop_core.citation_resolver as cr
    import loop_core.context_loader as cl
    import loop_core.loader_fields as lf
    import loop_core.loader_sections as lsec
    import loop_core.loader_summary as ls

    assert cl._TASK_ID_RE is lf._TASK_ID_RE
    assert cl._CITATION_TOKEN_RE is lf._CITATION_TOKEN_RE
    assert cl.extract_key_fields is lf.extract_key_fields
    assert cl._format_key_fields is lf._format_key_fields
    assert cl.CitationResolver is cr.CitationResolver
    assert cl.CitationResolution is cr.CitationResolution
    assert cl.repair_truncated_references is cr.repair_truncated_references
    assert cl._truncate_citation is cr._truncate_citation
    assert cl.UNRESOLVED_MARKER == cr.UNRESOLVED_MARKER
    assert cl.CITATION_MAX_CHARS == cr.CITATION_MAX_CHARS
    assert cl.summarize_text is ls.summarize_text
    assert cl.estimate_tokens is ls.estimate_tokens
    assert cl._level_line_params is ls._level_line_params
    assert cl._select_relevant_sections is lsec._select_relevant_sections
    assert cl._extract_framework_titles is lsec._extract_framework_titles
    assert cl._load_section_routing is lsec._load_section_routing
    assert cl._parse_front_matter_yaml is lsec._parse_front_matter_yaml
    # _ROUTING_CACHE 同一 dict 对象：tests/test_t0108_fixes.py 的
    # _ROUTING_CACHE.clear() 语义必须保持
    assert cl._ROUTING_CACHE is lsec._ROUTING_CACHE


def test_star_import_works():
    """from loop_core.X import * 可执行且公开面与 dir() 非下划线名一致。"""
    import loop_core.context_loader as cl
    import loop_core.human_review_packet as hrp

    ns = {}
    exec("from loop_core.human_review_packet import *", ns)  # noqa: S102 — 验收断言
    assert {k for k in ns if not k.startswith("_")} == {
        n for n in dir(hrp) if not n.startswith("_")
    }
    ns2 = {}
    exec("from loop_core.context_loader import *", ns2)  # noqa: S102 — 验收断言
    assert {k for k in ns2 if not k.startswith("_")} == {
        n for n in dir(cl) if not n.startswith("_")
    }


# ═══════════════════════════════════════════════════════════════════════
# 3. 循环导入规避（叶子先拆；新模块零反向引用壳）
# ═══════════════════════════════════════════════════════════════════════


_IMPORT_STMT_RE = re.compile(
    r"^\s*(?:from\s+loop_core\.[A-Za-z0-9_.]+\s+import|import\s+loop_core\.[A-Za-z0-9_.]+)\b",
    re.MULTILINE,
)


def _source_without_type_checking_guards(src: str) -> str:
    """去掉 TYPE_CHECKING 块（仅类型检查，运行时零导入）。"""
    return re.sub(
        r"if TYPE_CHECKING:.*?(?=\n\S|\Z)", "", src, flags=re.S)


def _loop_core_imports(src: str) -> list[str]:
    """提取源码中的 loop_core 导入语句（docstring 提及不算）。"""
    return [m.group(0).strip() for m in _IMPORT_STMT_RE.finditer(src)]


@pytest.mark.parametrize("module_name", [
    "loop_core.review_models",
    "loop_core.resume_payload",
    "loop_core.review_renderer",
])
def test_review_leaves_do_not_import_shell(module_name):
    """human_review_packet 新模块源码零反向引用壳（循环导入防线）。"""
    mod = importlib.import_module(module_name)
    src = _source_without_type_checking_guards(inspect.getsource(mod))
    imports = _loop_core_imports(src)
    assert all("human_review_packet" not in i for i in imports), imports


@pytest.mark.parametrize("module_name", [
    "loop_core.loader_fields",
    "loop_core.loader_summary",
    "loop_core.citation_resolver",
    "loop_core.loader_sections",
])
def test_loader_leaves_do_not_import_shell(module_name):
    """context_loader 新模块源码零反向引用壳（循环导入防线）。"""
    mod = importlib.import_module(module_name)
    src = _source_without_type_checking_guards(inspect.getsource(mod))
    imports = _loop_core_imports(src)
    assert all("context_loader" not in i for i in imports), imports


def test_dependency_dag_order():
    """叶子→壳依赖顺序：review_models/review_renderer/loader_fields/loader_sections
    零 loop_core 内部依赖；resume_payload 仅依赖 review_models；citation_resolver
    仅依赖 loader_fields；loader_summary 依赖 loader_fields+citation_resolver。"""
    import loop_core.citation_resolver as cr
    import loop_core.loader_fields as lf
    import loop_core.loader_sections as lsec
    import loop_core.loader_summary as ls
    import loop_core.resume_payload as rp
    import loop_core.review_models as rm
    import loop_core.review_renderer as rr

    for mod in (rm, rr, lf, lsec):
        importlib.import_module(mod.__name__)  # 已成功导入即无循环
    for mod in (rm, rr, lf, lsec):
        src = _source_without_type_checking_guards(inspect.getsource(mod))
        assert _loop_core_imports(src) == []  # 四叶子：零内部依赖
    rp_src = _source_without_type_checking_guards(inspect.getsource(rp))
    assert _loop_core_imports(rp_src) == ["from loop_core.review_models import"]
    cr_src = _source_without_type_checking_guards(inspect.getsource(cr))
    assert _loop_core_imports(cr_src) == ["from loop_core.loader_fields import"]
    ls_src = _source_without_type_checking_guards(inspect.getsource(ls))
    assert sorted(_loop_core_imports(ls_src)) == sorted([
        "from loop_core.loader_fields import",
        "from loop_core.citation_resolver import",
    ])


# ═══════════════════════════════════════════════════════════════════════
# 4. include_memories 默认 False 保持（T-0104 硬约束）
# ═══════════════════════════════════════════════════════════════════════


def test_include_memories_default_false_signature():
    """load_role_context / load_for_role 的 include_memories kwdefaults 保持 False。"""
    import loop_core.context_loader as cl

    assert cl.ContextLoader.load_role_context.__kwdefaults__[
        "include_memories"] is False
    assert cl.ContextLoader.load_for_role.__kwdefaults__[
        "include_memories"] is False
    assert cl.ContextLoader.load_role_context.__kwdefaults__[
        "memory_limit"] == 5
    assert cl.ContextLoader.load_for_role.__kwdefaults__[
        "memory_limit"] == 5


def test_include_memories_default_off_behavior():
    """默认（False）加载与显式 False 一致，且损坏知识库默认关闭不报错。"""
    from t0110_b2_golden import write_loader_fixture

    import loop_core.context_loader as cl
    from loop_core.knowledge_store import knowledge_path

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_loader_fixture(root, with_memories=True, memories_n=3)
        loader = cl.ContextLoader(root)
        default_ctx = loader.load_role_context("quality-engineer", complexity=0.9)
        off_ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9, include_memories=False)
        assert default_ctx.system_prompt == off_ctx.system_prompt
        assert "Related Memories" not in default_ctx.system_prompt

        # 损坏存储：默认关闭 = 不读知识库 = 不报错；显式开启 = fail-closed 抛错
        corrupt = root / "corrupt"
        write_loader_fixture(corrupt, with_memories=True, memories_n=1)
        knowledge_path(corrupt).write_text("{corrupt", encoding="utf-8")
        corrupt_loader = cl.ContextLoader(corrupt)
        ctx = corrupt_loader.load_role_context(
            "quality-engineer", complexity=0.9)
        assert "Related Memories" not in ctx.system_prompt
        with pytest.raises(Exception) as exc_info:
            corrupt_loader.load_role_context(
                "quality-engineer", complexity=0.9, include_memories=True)
        assert "KnowledgeStoreError" in type(exc_info.value).__name__


# ═══════════════════════════════════════════════════════════════════════
# 5. 内嵌抽查（自包含代表性断言）
# ═══════════════════════════════════════════════════════════════════════


def test_spot_check_human_review_packet():
    """渲染输出/恢复往返代表性断言（与 golden 同源但自包含）。"""
    from t0110_b2_golden import write_resume_fixture

    from loop_core.human_review_packet import (
        HumanReviewPacketBuilder,
        PacketType,
        build_resume_payload,
        resume_from_payload,
    )

    packet = HumanReviewPacketBuilder.from_phase_completion(
        "S6-delivery", "T-0110",
        {"architecture.md": "设计文档"}, {"quality-engineer": "通过"},
        {"pass": True, "checks": ["ok"]},
    )
    assert packet.packet_type == PacketType.GATE_APPROVAL
    md = packet.to_markdown()
    assert md.startswith("# Phase Delivery Decision Packet — Delivery")
    assert "## Key Choices" in md and "## You Need to Decide" in md
    plain = packet.to_plain_text()
    assert plain.startswith("PHASE DELIVERY DECISION PACKET — Delivery")
    assert "YOU NEED TO DECIDE" in plain

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_resume_fixture(root, with_task_file=True, with_evidence_dir=True)
        payload = build_resume_payload(
            root, task_id="T-0110", gate_id="G-T-0110-DELIVERY",
            phase="S6-delivery", decision_type=PacketType.GATE_APPROVAL,
        )
        assert payload.snapshot is not None
        assert len(payload.snapshot.context_pointers) == 5  # 3 sources + task + evidence
        ctx = resume_from_payload(payload, root)
        assert ctx.task_id == "T-0110" and ctx.phase == "S6-delivery"
        # TASK_GRAPH 夹具：T-0110 in_progress + T-0111 pending（T-0112 已完成）
        assert [t["id"] for t in ctx.pending_tasks] == ["T-0110", "T-0111"]


def test_spot_check_context_loader():
    """摘要/引用修复/节选择代表性断言（与 golden 同源但自包含）。"""
    from loop_core.context_loader import (
        ContextLoader,
        _select_relevant_sections,
        estimate_tokens,
        repair_truncated_references,
        summarize_text,
    )

    summary = summarize_text(
        "## 背景\n任务 T-0101 在 S4-implementation 完成，状态 APPROVED。\n"
        "task_id: T-0101\n决策点：是否批准进入 S5-quality。\n",
        level=1,
    )
    assert "[CONTEXT SUMMARY L1]" in summary
    assert "T-0101" in summary and "S4-implementation" in summary
    assert estimate_tokens("") == 0
    assert estimate_tokens("中文测试") == 8

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".ai" / "evidence" / "T-0101").mkdir(parents=True)
        (root / ".ai" / "evidence" / "T-0101" / "a.md").write_text(
            "# a", encoding="utf-8")
        repaired, resolutions = repair_truncated_references(
            "见 …/T-0101/a.md 与 evidence/T-9999/missing.md", root)
        assert ".ai/evidence/T-0101/a.md" in repaired
        assert "[UNRESOLVED: evidence/T-9999/missing.md]" in repaired
        # token 按长度降序处理：更长的 missing 引用先被解析
        assert sorted(r.status for r in resolutions) == ["NOT_FOUND", "RESOLVED"]

        doc = root / "architecture.md"
        doc.write_text("## Quality Gate\n内容\n## Deployment\n内容\n",
                       encoding="utf-8")
        loader = ContextLoader(root)
        idx = loader.build_document_index(str(doc))
        assert _select_relevant_sections("quality-engineer", idx) == [
            "Quality Gate"]
        assert _select_relevant_sections("unknown-role", idx) == [
            "Quality Gate", "Deployment"]
        section = loader.load_document_section(str(doc), "Deployment")
        assert section == "## Deployment\n内容"


def test_routing_cache_clear_still_works():
    """test_t0108_fixes 依赖的 _ROUTING_CACHE.clear() 语义保持（同一对象）。"""
    import loop_core.context_loader as cl
    import loop_core.loader_sections as lsec

    assert cl._ROUTING_CACHE is lsec._ROUTING_CACHE
    lsec._ROUTING_CACHE.clear()  # 与既有测试同样的清缓存调用
    assert len(lsec._ROUTING_CACHE) == 0
