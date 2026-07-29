"""Structural quality checks wrapper. Calls all 6 static analysis modules."""
import os, sys, json
from pathlib import Path

def _label(name): return {0:name,1:0,2:0,3:Q+Q}
def run_structural_checks(project_root=None):
    root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
    results = []
    
    # 1. static_analyzer
    try:
        from codex_loop.core.static_analyzer import analyze_project
        r = analyze_project(str(root))
        results.append({"name": "static_analysis", "value": len(r.errors), "threshold": 0, "raw": str(r.errors)[:300]})
    except Exception as e:
        results.append({"name": "static_analysis", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    # 2. security_scanner
    try:
        from codex_loop.core.security_scanner import scan_security
        r = scan_security(str(root))
        vulns = len(r.critical) + len(r.high)
        results.append({"name": "security_scan", "value": vulns, "threshold": 0, "raw": "critical="+str(len(r.critical))+", high="+str(len(r.high))})
    except Exception as e:
        results.append({"name": "security_scan", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    # 3. design_reviewer
    try:
        from codex_loop.core.design_reviewer import review_design
        r = review_design(str(root))
        results.append({"name": "design_review", "value": len(r.errors), "threshold": 0, "raw": str(r.errors)[:300]})
    except Exception as e:
        results.append({"name": "design_review", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    # 4. import_checker
    try:
        from codex_loop.core.import_checker import ImportChecker
        checker = ImportChecker(str(root))
        r = checker.check_directory()
        results.append({"name": "import_check", "value": len(r.violations), "threshold": 0, "raw": str(r.violations)[:300]})
    except Exception as e:
        results.append({"name": "import_check", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    # 5. contract_verifier
    try:
        from codex_loop.core.contract_verifier import check_contract_test_coverage
        r = check_contract_test_coverage(str(root))
        results.append({"name": "contract_verify", "value": 0 if r.is_clean() else 1, "threshold": 0, "raw": str(len(r.contracts)) if hasattr(r,'contracts') else 'ok'})
    except Exception as e:
        results.append({"name": "contract_verify", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    # 6. subagent_evidence_verifier
    try:
        from codex_loop.core.subagent_evidence_verifier import verify_review_evidence
        evdir = root / '.ai' / 'evidence'
        if evdir.exists():
            files = list(evdir.rglob('*.json'))[:10]
            issues = [ef.name for ef in files if not verify_review_evidence(str(ef)).get('valid')]
            results.append({"name": "subagent_evidence", "value": len(issues), "threshold": 0, "raw": str(issues)[:300]})
        else:
            results.append({"name": "subagent_evidence", "value": 0, "threshold": 0, "raw": "no evidence dir"})
    except Exception as e:
        results.append({"name": "subagent_evidence", "value": -1, "threshold": 0, "raw": str(e)[:200], "skipped": True})

    return results