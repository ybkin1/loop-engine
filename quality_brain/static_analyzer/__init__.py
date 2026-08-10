"""增强静态分析器 — 50+ 条确定性规则，检测 AI 特有代码质量问题。

规则分 6 类：
- error_handling: 错误处理 (EH-001 ~ EH-008)
- input_validation: 输入验证 (IV-001 ~ IV-006)
- ai_anti_patterns: AI 特有反模式 (AI-001 ~ AI-012) ★ 最重要
- security_patterns: 安全模式 (SE-001 ~ SE-008)
- code_quality: 代码质量 (CQ-001 ~ CQ-010)
- resource_perf: 资源与性能 (RP-001 ~ RP-006)
"""

import ast
import os
import re
from pathlib import Path
from typing import Callable, Optional

from ..core import Violation, Severity

# 规则函数签名: (ast.AST, str, str) -> Optional[Violation]
# 参数: AST树, 源文件内容, 文件路径
RuleFunc = Callable[[ast.AST, str, str], list[Violation]]


class StaticAnalyzer:
    """聚合所有静态分析规则，对源代码目录执行批量检查。"""

    def __init__(self):
        self._rules: list[tuple[str, RuleFunc, str]] = []  # (rule_id, func, category)

    def register(self, rule_id: str, func: RuleFunc, category: str = ""):
        self._rules.append((rule_id, func, category))

    def analyze_file(self, file_path: str) -> list[Violation]:
        """分析单个文件，返回所有违规。"""
        violations = []
        path = Path(file_path)
        if not path.exists() or path.suffix != '.py':
            return violations
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            violations.append(Violation(
                rule_id="SYNTAX-ERROR", severity=Severity.HIGH,
                message=f"无法解析: {file_path}", file_path=file_path))
            return violations

        for rule_id, func, _ in self._rules:
            try:
                vlist = func(tree, source, str(path))
                for v in vlist:
                    v.rule_id = rule_id
                    if not v.file_path:
                        v.file_path = file_path
                violations.extend(vlist)
            except Exception as e:
                violations.append(Violation(
                    rule_id=rule_id, severity=Severity.MEDIUM,
                    message=f"规则 {rule_id} 执行失败: {e}", file_path=file_path))
        return violations

    def analyze_directory(self, root_dir: str) -> list[Violation]:
        """递归分析目录下所有 Python 文件。"""
        violations = []
        for dirpath, _, filenames in os.walk(root_dir):
            # 跳过虚拟环境、缓存、测试 fixtures
            if any(skip in dirpath for skip in ['__pycache__', '.venv', 'venv', 'node_modules', '.git']):
                continue
            for fname in filenames:
                if fname.endswith('.py'):
                    violations.extend(self.analyze_file(os.path.join(dirpath, fname)))
        return violations

    def summary(self, violations: list[Violation]) -> dict:
        """生成违规摘要。"""
        counts = {"BLOCKER": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        by_category: dict[str, int] = {}
        for v in violations:
            counts[v.severity.value] += 1
            # 从 rule_id 提取分类
            cat = v.rule_id.split('-')[0] if '-' in v.rule_id else 'other'
            by_category[cat] = by_category.get(cat, 0) + 1
        return {
            "total": len(violations),
            "by_severity": counts,
            "by_category": by_category,
            "blocker_count": counts["BLOCKER"],
            "has_blockers": counts["BLOCKER"] > 0,
        }


def load_all_rules() -> StaticAnalyzer:
    """加载全部 50+ 条规则。"""
    from . import error_handling, input_validation, ai_anti_patterns
    from . import security_patterns, code_quality, resource_perf

    analyzer = StaticAnalyzer()

    for mod in [error_handling, input_validation, ai_anti_patterns,
                security_patterns, code_quality, resource_perf]:
        for name in dir(mod):
            if name.startswith('RULE_'):
                rule = getattr(mod, name)
                if callable(rule):
                    analyzer.register(name, rule, mod.__name__.split('.')[-1])

    return analyzer
