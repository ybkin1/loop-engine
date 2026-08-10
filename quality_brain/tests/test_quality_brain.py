"""Quality Brain 测试套件。

验证静态分析器能正确检测已知的 AI 代码缺陷。
"""

import os
import tempfile
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quality_brain.static_analyzer import load_all_rules
from quality_brain.core import Severity


@pytest.fixture
def analyzer():
    return load_all_rules()


def _analyze(analyzer, source_code: str) -> dict:
    """运行分析并返回按规则ID分组的违规。"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source_code)
        tmpfile = f.name
    try:
        violations = analyzer.analyze_file(tmpfile)
    finally:
        os.unlink(tmpfile)

    by_rule = {}
    for v in violations:
        by_rule.setdefault(v.rule_id, []).append(v)
    return by_rule


class TestErrorHandling:
    """错误处理规则测试。"""

    def test_EH001_bare_except(self, analyzer):
        code = """
def foo():
    try:
        do_something()
    except:
        pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_EH_001' in v, "应该检测到裸 except:"
        assert v['RULE_EH_001'][0].severity == Severity.HIGH

    def test_EH002_except_pass(self, analyzer):
        code = """
def foo():
    try:
        do_something()
    except Exception:
        pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_EH_002' in v, "应该检测到 except:pass"

    def test_EH004_open_no_with(self, analyzer):
        code = """
def read_file(path):
    f = open(path)
    return f.read()
"""
        v = _analyze(analyzer, code)
        assert 'RULE_EH_004' in v, "应该检测到 open() 无 with"


class TestAIAntiPatterns:
    """AI 反模式测试 — 最重要。"""

    def test_AI001_dead_function(self, analyzer):
        code = """
def helper():
    return 42

def used_function():
    return helper()

result = used_function()
"""
        v = _analyze(analyzer, code)
        # helper() IS called inside used_function() — 不应该被标记
        assert 'RULE_AI_001' not in v, "helper() 被调用，不应标记为死代码"

    def test_AI001_truly_dead(self, analyzer):
        code = """
def dead_func():
    return complex_logic()

def main():
    return 42  # dead_func never called
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_001' in v, "dead_func() 从未被调用"

    def test_AI003_unused_variable(self, analyzer):
        code = """
def foo():
    x = 1
    used = 2
    return used
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_003' in v, "x 赋值后未使用"

    def test_AI004_local_import(self, analyzer):
        code = """
def foo():
    import os
    return os.getcwd()
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_004' in v, "函数内局部 import"

    def test_AI006_docstring_param_mismatch(self, analyzer):
        code = """
def authenticate(username):
    \"\"\"
    Authenticate user.
    :param user: The username
    :param token: Auth token
    \"\"\"
    pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_006' in v, "docstring 引用了不存在的参数 token"

    def test_AI007_unreachable_code(self, analyzer):
        code = """
def foo():
    return 1
    x = 2
    print(x)
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_007' in v, "return 后不可达代码"

    def test_AI009_too_many_todos(self, analyzer):
        code = """
# TODO: fix this
# TODO: fix that
# TODO: also this
# TODO: and this one too
def foo():
    pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_AI_009' in v, "超过 3 处 TODO"


class TestSecurityPatterns:
    """安全模式规则测试。"""

    def test_SE001_hardcoded_password(self, analyzer):
        code = """
def connect():
    password = 's3cret_p4ss!'
    return password
"""
        v = _analyze(analyzer, code)
        assert 'RULE_SE_001' in v, "应该检测到硬编码密码"

    def test_SE001_excluded_placeholder(self, analyzer):
        code = """
def connect():
    password = 'your_password_here'
    return password
"""
        v = _analyze(analyzer, code)
        assert 'RULE_SE_001' not in v, "占位符密码不应被检测"

    def test_SE002_os_system(self, analyzer):
        code = """
import os
def run(cmd):
    os.system(cmd)
"""
        v = _analyze(analyzer, code)
        assert 'RULE_SE_002' in v, "应该检测到 os.system()"

    def test_SE003_eval(self, analyzer):
        code = """
def run(expr):
    return eval(expr)
"""
        v = _analyze(analyzer, code)
        assert 'RULE_SE_003' in v, "应该检测到 eval() 动态参数"

    def test_SE006_sql_injection_fstring(self, analyzer):
        code = """
def get_user(name):
    cursor.execute(f"SELECT * FROM users WHERE name='{name}'")
"""
        v = _analyze(analyzer, code)
        # RULE_IV_003 catches f-string SQL (BLOCKER)
        assert 'RULE_IV_003' in v, "应该检测到 SQL 拼接"


class TestCodeQuality:
    """代码质量规则测试。"""

    def test_CQ001_too_many_params(self, analyzer):
        code = """
def foo(a, b, c, d, e, f, g, h, i, j):
    pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_CQ_001' in v, "超过 8 个参数"

    def test_CQ007_mutable_default(self, analyzer):
        code = """
def foo(items=[]):
    pass
"""
        v = _analyze(analyzer, code)
        assert 'RULE_CQ_007' in v, "可变默认参数"


class TestResourcePerf:
    """资源性能规则测试。"""

    def test_RP004_recursion_no_limit(self, analyzer):
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        v = _analyze(analyzer, code)
        assert 'RULE_RP_004' in v, "递归无深度限制"

    def test_RP005_range_len(self, analyzer):
        code = """
items = [1, 2, 3]
for i in range(len(items)):
    print(items[i])
"""
        v = _analyze(analyzer, code)
        assert 'RULE_RP_005' in v, "range(len(...)) 应用 enumerate"


class TestGateAggregator:
    """Gate 决策矩阵测试。"""

    def test_all_clear(self):
        from quality_brain.gate_aggregator import GateAggregator, GateDecision
        agg = GateAggregator()
        result = agg.evaluate(
            {'quality-engineer': {'lint_errors': 0, 'test_pass_rate': 100, 'coverage': 85},
             'security-engineer': {'critical': 0, 'high': 0},
             'independent-reviewer': {'verdict': 'APPROVED'},
             'evidence-verifier': {'missing': 0, 'stale': 0, 'forged': 0},
             'contract-verifier': {'blockers': 0},
             'import-checker': {'undeclared': 0}},
            [], 'S4'
        )
        assert result.decision == GateDecision.GO

    def test_blocked_by_brain(self):
        from quality_brain.gate_aggregator import GateAggregator, GateDecision
        from quality_brain.core import Blocker
        agg = GateAggregator()
        violations = [Blocker("SQL 注入")]
        result = agg.evaluate(
            {'quality-engineer': {'lint_errors': 0, 'test_pass_rate': 100, 'coverage': 85},
             'security-engineer': {'critical': 0, 'high': 0},
             'independent-reviewer': {'verdict': 'APPROVED'},
             'evidence-verifier': {'missing': 0, 'stale': 0, 'forged': 0},
             'contract-verifier': {'blockers': 0},
             'import-checker': {'undeclared': 0}},
            violations, 'S4'
        )
        assert result.decision == GateDecision.BLOCKED

    def test_blocked_by_lint(self):
        from quality_brain.gate_aggregator import GateAggregator, GateDecision
        agg = GateAggregator()
        result = agg.evaluate(
            {'quality-engineer': {'lint_errors': 5, 'test_pass_rate': 100, 'coverage': 85},
             'security-engineer': {'critical': 0, 'high': 0},
             'independent-reviewer': {'verdict': 'APPROVED'},
             'evidence-verifier': {'missing': 0, 'stale': 0, 'forged': 0},
             'contract-verifier': {'blockers': 0},
             'import-checker': {'undeclared': 0}},
            [], 'S4'
        )
        assert result.decision == GateDecision.BLOCKED

    def test_conditional(self):
        from quality_brain.gate_aggregator import GateAggregator, GateDecision
        agg = GateAggregator()
        result = agg.evaluate(
            {'quality-engineer': {'lint_errors': 0, 'test_pass_rate': 100, 'coverage': 85},
             'security-engineer': {'critical': 0, 'high': 2},
             'independent-reviewer': {'verdict': 'CHANGES_REQUESTED'},
             'evidence-verifier': {'missing': 0, 'stale': 0, 'forged': 0},
             'contract-verifier': {'blockers': 0},
             'import-checker': {'undeclared': 0}},
            [], 'S4'
        )
        assert result.decision == GateDecision.CONDITIONAL_GO
