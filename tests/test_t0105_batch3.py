"""
T-0105 批 3 — Q2 教学式多轮提问（B-1）+ Q4 低成本原型机制（B-2）测试。

Covers:
- Q2 多轮澄清（inbox）：ask_clarification 对已有条目追加问题轮次
  （问题累积 / rounds 计数 / NEW→CLARIFYING / 空问题报错）；
  add_clarification_questions 替换语义保留；clarification_rounds 字段
  向后兼容（旧 YAML 无该字段 → 默认 0）；MCP inbox_ask_clarification
- Q2 提示词层：product-manager SKILL"缺口识别 + 教学式提问"节（三栏清单 /
  每轮≤3 / 为什么问 / 可多轮）；main-thread CONTRACT R11 新语义
  （同一轮≤3、可多轮；保留 R11 编号与主体语义；旧硬上限措辞消失）
- Q4 原型机制（planner）：generate_prototype 三种形态（html_mock /
  cli_demo / data_sample），task_type=prototype、S3-interface 阶段、
  低成本可迭代 AC、序列化往返、旧 plan 文件无 task_type → 默认 standard；
  MCP planner_generate_prototype
- Q4 模板层：gate-request"选择后反馈（方案修正循环）"节；
  task-card"原型交付（Q4，可选）"节 + 原型三原则
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.inbox import Inbox, InboxError, InboxStatus  # noqa: E402
from loop_core.planner import (  # noqa: E402
    PlanStatus,
    Planner,
    PlannerError,
    PrototypeForm,
    TaskType,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = PROJECT_ROOT / "agents" / "main-thread" / "CONTRACT.yaml"
PM_SKILL = PROJECT_ROOT / "agents" / "product-manager" / "SKILL.md"
GATE_REQUEST = PROJECT_ROOT / "skills" / "loop-governance" / "templates" / "gate-request.md"
TASK_CARD = PROJECT_ROOT / "skills" / "loop-governance" / "templates" / "task-card.md"


# ── helpers ──────────────────────────────────────────────────────────────

def _load_tool_module(name: str):
    path = PROJECT_ROOT / "tools" / f"tool_{name}.py"
    spec = importlib.util.spec_from_file_location(f"tool_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_root():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ── Q2：inbox 多轮澄清 ───────────────────────────────────────────────────

class TestQ2MultiRoundClarification:
    def test_ask_clarification_appends_rounds(self, tmp_root):
        """多轮追加：问题跨轮累积，rounds 计数递增。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("记账应用", "想要一个手机记账应用。")
        r1 = inbox.ask_clarification(req.requirement_id, ["Q1：单人还是家庭共管？"])
        r2 = inbox.ask_clarification(r1.requirement_id, ["Q2：随手记还是月底对账？"])
        r3 = inbox.ask_clarification(r2.requirement_id, ["Q3：要不要分类标签？"])
        assert r3.clarification_questions == [
            "Q1：单人还是家庭共管？",
            "Q2：随手记还是月底对账？",
            "Q3：要不要分类标签？",
        ]
        assert r3.clarification_rounds == 3

    def test_first_ask_moves_new_to_clarifying(self, tmp_root):
        """首轮提问：NEW → CLARIFYING。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("模糊需求", "描述不完整。")
        r = inbox.ask_clarification(req.requirement_id, ["Q1"])
        assert r.status == InboxStatus.CLARIFYING

    def test_later_rounds_keep_clarifying(self, tmp_root):
        """追加轮次保持 CLARIFYING，状态不漂移。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("需求", "描述。")
        inbox.ask_clarification(req.requirement_id, ["Q1"])
        r2 = inbox.ask_clarification(req.requirement_id, ["Q2"])
        assert r2.status == InboxStatus.CLARIFYING
        assert r2.clarification_rounds == 2

    def test_empty_questions_raise(self, tmp_root):
        """空问题列表报 InboxError（fail-closed）。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("需求", "描述。")
        with pytest.raises(InboxError):
            inbox.ask_clarification(req.requirement_id, [])

    def test_legacy_add_replaces_and_sets_rounds(self, tmp_root):
        """旧方法替换语义保留，rounds 至少为 1。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("需求", "描述。")
        u = inbox.add_clarification_questions(req.requirement_id, ["Q1", "Q2"])
        assert u.clarification_questions == ["Q1", "Q2"]
        assert u.clarification_rounds == 1
        # 替换语义：再调用直接覆盖，不累积
        u2 = inbox.add_clarification_questions(req.requirement_id, ["Q3"])
        assert u2.clarification_questions == ["Q3"]
        assert u2.clarification_rounds == 1

    def test_rounds_field_backward_compat(self, tmp_root):
        """旧 YAML 无 clarification_rounds → 默认 0，加载不报错。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("旧需求", "描述。")
        # 手工抹掉新字段，模拟旧文件
        import yaml
        path = tmp_root / ".ai" / "inbox" / f"{req.requirement_id}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data.pop("clarification_rounds")
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        loaded = inbox.get(req.requirement_id)
        assert loaded.clarification_rounds == 0
        assert loaded.clarification_questions == []

    def test_roundtrip_keeps_rounds(self, tmp_root):
        """to_dict/from_dict 往返保留 clarification_rounds。"""
        inbox = Inbox(tmp_root)
        req = inbox.submit("需求", "描述。")
        inbox.ask_clarification(req.requirement_id, ["Q1"])
        inbox.ask_clarification(req.requirement_id, ["Q2"])
        d = inbox.get(req.requirement_id).to_dict()
        assert d["clarification_rounds"] == 2
        assert d["clarification_questions"] == ["Q1", "Q2"]

    def test_tool_inbox_ask_clarification(self, tmp_root, monkeypatch):
        """MCP 工具 inbox_ask_clarification 追加问题并返回累积结果。"""
        monkeypatch.setenv("LOOP_PROJECT_ROOT", str(tmp_root))
        tool = _load_tool_module("inbox")
        inbox = Inbox(tmp_root)
        req = inbox.submit("需求", "描述。")
        out = tool.handle_ask_clarification({
            "requirement_id": req.requirement_id,
            "questions": ["Q1", "Q2"],
        })
        import json
        payload = json.loads(out)
        assert payload["success"] is True
        assert payload["data"]["clarification_questions"] == ["Q1", "Q2"]
        assert payload["data"]["clarification_rounds"] == 1
        # 第二轮追加
        out2 = tool.handle_ask_clarification({
            "requirement_id": req.requirement_id,
            "questions": ["Q3"],
        })
        payload2 = json.loads(out2)
        assert payload2["data"]["clarification_questions"] == ["Q1", "Q2", "Q3"]
        assert payload2["data"]["clarification_rounds"] == 2

    def test_tool_inbox_ask_clarification_rejects_bad_args(self, tmp_root, monkeypatch):
        monkeypatch.setenv("LOOP_PROJECT_ROOT", str(tmp_root))
        tool = _load_tool_module("inbox")
        out = tool.handle_ask_clarification({"requirement_id": "", "questions": ["Q"]})
        assert '"success": false' in out
        out2 = tool.handle_ask_clarification({"requirement_id": "REQ-x", "questions": []})
        assert '"success": false' in out2


# ── Q2：提示词层（缺口识别 + 教学式提问 / R11 新语义） ────────────────────

class TestQ2PromptLayer:
    def test_product_manager_has_gap_identification_section(self):
        text = PM_SKILL.read_text(encoding="utf-8")
        assert "## 14. 缺口识别 + 教学式提问（Q2）" in text
        # 三栏清单：用户已知 / 缺什么 / 缺口如何影响结果
        assert "缺口如何影响结果" in text
        # 每个问题附"为什么问"
        assert "为什么问" in text
        # 每轮 ≤3 个、可多轮
        assert "每轮最多 3 个问题" in text
        assert "可多轮" in text
        # 多轮闭环引用 ask_clarification
        assert "ask_clarification" in text

    def test_r11_new_semantics_in_contract(self):
        text = CONTRACT.read_text(encoding="utf-8")
        # R11 编号保留
        assert "R11_reduce_questions" in text
        # 新语义：同一轮 ≤3 个、可多轮
        assert "同一轮提问不超过 3 个" in text
        assert "可多轮" in text
        # 主体语义保留：非关键决策自行处理并标注
        assert "非关键决策自行处理并标注" in text
        # 旧硬上限措辞消失
        assert "同一阶段内向用户提问不超过 3 次" not in text


# ── Q4：planner 原型任务类型 ─────────────────────────────────────────────

class TestQ4PrototypePlanner:
    @pytest.mark.parametrize("form", [
        PrototypeForm.HTML_MOCK,
        PrototypeForm.CLI_DEMO,
        PrototypeForm.DATA_SAMPLE,
    ])
    def test_generate_prototype_three_forms(self, tmp_root, form):
        planner = Planner(tmp_root)
        draft = planner.generate_prototype(
            "记账界面", "做一个让用户判断录入流程的原型", "REQ-20260803-001", form
        )
        assert draft.plan_id.startswith("PLAN-")
        assert draft.status == PlanStatus.DRAFT
        assert len(draft.tasks) == 1
        task = draft.tasks[0]
        assert task.task_type == TaskType.PROTOTYPE.value
        assert task.prototype_form == form.value
        assert task.phase == "S3-interface"

    def test_prototype_acceptance_criteria_cheap_iterative(self, tmp_root):
        """原型 AC：低成本 / 可迭代 / 不追求完整。"""
        planner = Planner(tmp_root)
        draft = planner.generate_prototype("CLI 演示", "演示主流程", None, "cli_demo")
        ac_text = " ".join(draft.tasks[0].acceptance_criteria)
        assert "低成本" in ac_text
        assert "可迭代" in ac_text
        assert "不追求完整" in ac_text
        assert "选择后反馈" in ac_text

    def test_prototype_persistence_roundtrip(self, tmp_root):
        """原型 plan 落盘后可重载，task_type/prototype_form 不丢。"""
        planner = Planner(tmp_root)
        draft = planner.generate_prototype("数据样本", "示例数据", None, "data_sample")
        planner2 = Planner(tmp_root)
        loaded = planner2.get(draft.plan_id)
        t = loaded.tasks[0]
        assert t.task_type == "prototype"
        assert t.prototype_form == "data_sample"

    def test_legacy_plan_without_task_type_defaults_standard(self, tmp_root):
        """旧 plan 文件无 task_type/prototype_form → 默认 standard / 空。"""
        planner = Planner(tmp_root)
        draft = planner.generate("旧功能", "普通需求。")
        # 手工移除新字段模拟旧文件
        import yaml
        path = tmp_root / ".ai" / "plans" / f"{draft.plan_id}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for t in data["tasks"]:
            t.pop("task_type", None)
            t.pop("prototype_form", None)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        planner2 = Planner(tmp_root)
        loaded = planner2.get(draft.plan_id)
        assert all(t.task_type == "standard" for t in loaded.tasks)
        assert all(t.prototype_form == "" for t in loaded.tasks)

    def test_standard_generate_unchanged(self, tmp_root):
        """generate() 仍产出 standard 任务，不出现原型字段污染。"""
        planner = Planner(tmp_root)
        draft = planner.generate("普通需求", "实现一个功能。")
        assert all(t.task_type == "standard" for t in draft.tasks)
        assert all(t.prototype_form == "" for t in draft.tasks)

    def test_generate_prototype_empty_desc_raises(self, tmp_root):
        planner = Planner(tmp_root)
        with pytest.raises(PlannerError):
            planner.generate_prototype("标题", "  ")

    def test_tool_planner_generate_prototype(self, tmp_root, monkeypatch):
        """MCP 工具 planner_generate_prototype 三种形态均可用。"""
        monkeypatch.setenv("LOOP_PROJECT_ROOT", str(tmp_root))
        tool = _load_tool_module("planner")
        import json
        out = tool.handle_generate_prototype({
            "title": "登录页原型",
            "description": "让用户确认登录流程",
            "prototype_form": "html_mock",
        })
        payload = json.loads(out)
        assert payload["success"] is True
        task = payload["data"]["tasks"][0]
        assert task["task_type"] == "prototype"
        assert task["prototype_form"] == "html_mock"

    def test_tool_planner_rejects_bad_form(self, tmp_root, monkeypatch):
        monkeypatch.setenv("LOOP_PROJECT_ROOT", str(tmp_root))
        tool = _load_tool_module("planner")
        out = tool.handle_generate_prototype({
            "title": "x", "description": "y", "prototype_form": "video",
        })
        assert '"success": false' in out


# ── Q4：模板层（gate-request 反馈字段 / task-card 原型说明） ──────────────

class TestQ4TemplateLayer:
    def test_gate_request_has_selection_feedback(self):
        text = GATE_REQUEST.read_text(encoding="utf-8")
        assert "## 选择后反馈（方案修正循环）" in text
        assert "选择理由" in text
        assert "AI 据此调整" in text
        assert "一轮" in text

    def test_task_card_has_prototype_section(self):
        text = TASK_CARD.read_text(encoding="utf-8")
        assert "## 原型交付（Q4，可选）" in text
        assert "HTML mock" in text
        assert "CLI demo" in text
        assert "数据样本" in text
        assert "不追求完整" in text
        assert "低成本" in text
        assert "可迭代" in text

    def test_task_card_section_order_preserved(self):
        """新增节不破坏既有节顺序（test_t0104_templates 顺序断言兼容）。"""
        text = TASK_CARD.read_text(encoding="utf-8")
        order = [
            "## 基本信息",
            "## 信息完整度声明 + 象限判定（必填）",
            "## 用户可见目标",
            "## 相关经验与不熟悉处（必填）",
            "## 范围与边界",
            "## 原型交付（Q4，可选）",
            "## 盲点清单（必填，≥3 条）",
            "## 验收标准",
        ]
        positions = [text.index(marker) for marker in order]
        assert positions == sorted(positions), "节顺序错误"
