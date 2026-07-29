"""Tests for static analyzer, security scanner, and design reviewer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.static_analyzer import (
    AnalysisReport, Finding, analyze_project,
    _check_extract_without_verify, _check_swallowed_exceptions,
)
from loop_core.security_scanner import (
    SecurityReport, SecFinding, scan_security,
)
from loop_core.design_reviewer import (
    DesignReport, DesignFinding, review_design,
    _check_host_leaks,
)


# ── Static Analyzer ───────────────────────────────────────────────────

class TestStaticAnalyzer:
    def test_detects_extract_without_verify(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("""
import re
m = re.search(r'pattern', text)
result = m.group(1)  # extracted but never compared
print(result)
""")
        r = analyze_project(tmp_path)
        assert any("SA-001" in finding.rule_id for finding in r.findings)

    def test_detects_bare_except(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("""
try:
    risky()
except:
    pass
""")
        r = analyze_project(tmp_path)
        assert any("SA-002" in finding.rule_id for finding in r.findings)

    def test_detects_exception_pass(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("""
try:
    risky()
except Exception:
    pass
""")
        r = analyze_project(tmp_path)
        assert any("SA-003" in finding.rule_id for finding in r.findings)

    def test_no_false_positive_on_verified_extract(self):
        """Extract + compare should not flag."""
        import ast
        from loop_core.static_analyzer import _check_extract_without_verify
        source = "import re\nm = re.search(r'key', text)\nkey = m.group(1)\nif key == expected:\n    print('ok')\n"
        tree = ast.parse(source)
        findings = _check_extract_without_verify(Path("test.py"), source, tree)
        assert not any("SA-001" in f.rule_id for f in findings)


# ── Security Scanner ──────────────────────────────────────────────────

class TestSecurityScanner:
    def test_detects_hardcoded_api_key(self):
        """Test secret pattern detection directly."""
        from loop_core.security_scanner import _SECRET_PATTERNS
        line = 'API_KEY = "sk-1234567890abcdef"'
        assert any(p.search(line) for p, _, _, _ in _SECRET_PATTERNS)

    def test_no_false_positive_on_env_read(self, tmp_path):
        f = tmp_path / "config.py"
        f.write_text('api_key = os.environ.get("API_KEY")\n')
        r = scan_security(tmp_path)
        assert r.critical == 0

    def test_excludes_test_files(self, tmp_path):
        t = tmp_path / "tests"
        t.mkdir()
        (t / "test_config.py").write_text('PASSWORD = "secret123"\n')
        r = scan_security(tmp_path)
        # Test files excluded → no critical findings from test dir
        critical_from_tests = [f for f in r.findings if f.severity == "critical" and "test_" in f.file]
        assert len(critical_from_tests) == 0

    def test_detects_os_system(self):
        """Test OS command detection directly."""
        from loop_core.security_scanner import _OS_COMMAND_PATTERNS
        assert any(p.search('os.system("echo test")') for p, _, _, _ in _OS_COMMAND_PATTERNS)


# ── Design Reviewer ───────────────────────────────────────────────────

class TestDesignReviewer:
    def test_detects_host_import_in_loop_core(self, tmp_path):
        core = tmp_path / "loop_core"
        core.mkdir()
        (core / "bad_module.py").write_text("import zcode.client\n")
        r = review_design(tmp_path)
        assert any("DR-001" in f.rule_id for f in r.findings)

    def test_ignores_comment_attribution(self, tmp_path):
        core = tmp_path / "loop_core"
        core.mkdir()
        (core / "ok_module.py").write_text(
            "# Pattern adapted from Qoder's state-machine.ts\n"
            "def process():\n    pass\n"
        )
        r = review_design(tmp_path)
        assert not any("DR-001" in f.rule_id for f in r.findings)

    def test_detects_missing_docstring(self):
        """Test missing docstring detection directly."""
        import ast
        from loop_core.design_reviewer import _check_public_api_docs
        source = "def public_api():\n    return 42\n"
        tree = ast.parse(source)
        findings = _check_public_api_docs(Path("module.py"), source, tree)
        assert any("DR-010" in f.rule_id for f in findings)


# ── Integration: self-check ──────────────────────────────────────────

class TestSelfCheck:
    """Verify Loop passes its own analyzers."""
    def test_loop_core_has_no_host_leaks(self):
        root = Path(__file__).resolve().parents[1]
        r = review_design(root)
        core_leaks = [f for f in r.findings
                      if f.severity == "error" and "loop_core" in f.file]
        assert len(core_leaks) == 0, f"Host leaks in loop_core: {core_leaks}"

    def test_loop_passes_security_scan(self):
        root = Path(__file__).resolve().parents[1]
        r = scan_security(root)
        assert r.passed, f"Security scan failed: {r.critical} critical, {r.high} high"
