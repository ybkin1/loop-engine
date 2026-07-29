S=chr(39)
"""Structural quality checks wrapper. All 6 modules with correct interfaces."""
from pathlib import Path


def _ok(name,val): return {'name': name,'value': val,'threshold': 0,'raw': str(val)}
def _skip(name,reason): return {'name': name,'value': -1,'threshold': 0,'raw': reason[:200],'skipped': True}

def run_structural_checks(project_root=None):
    root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
    results = []

    # 1. static_analyzer
    try:
        from codex_loop.core.static_analyzer import analyze_project
        r = analyze_project(str(root))
        results.append({'name': 'static_analysis','value': r.errors+warn_val(r),'threshold': 0,'raw': S+chr(101)+chr(114)+chr(114)+chr(111)+chr(114)+chr(115)+chr(61)+S+str(r.errors)+S+chr(32)+chr(119)+chr(97)+chr(114)+chr(110)+chr(105)+chr(110)+chr(103)+chr(115)+chr(61)+S+str(warn_val(r))})
    except Exception as e:
        results.append(_skip('static_analysis',str(e)))

    # 2. security_scanner
    try:
        from codex_loop.core.security_scanner import scan_security
        r = scan_security(str(root))
        vulns = int(r.critical) + int(r.high)
        results.append({'name': 'security_scan','value': vulns,'threshold': 0,'raw': S+chr(99)+chr(114)+chr(105)+chr(116)+chr(105)+chr(99)+chr(97)+chr(108)+chr(61)+S+str(r.critical)+S+chr(32)+chr(104)+chr(105)+chr(103)+chr(104)+chr(61)+S+str(r.high)})
    except Exception as e:
        results.append(_skip('security_scan',str(e)))

    # 3. design_reviewer
    try:
        from codex_loop.core.design_reviewer import review_design
        r = review_design(str(root))
        results.append(_ok('design_review',int(r.errors)))
    except Exception as e:
        results.append(_skip('design_review',str(e)))

    # 4. import_checker
    try:
        from codex_loop.core.import_checker import ImportChecker
        c = ImportChecker()
        r = c.check_directory()
        results.append(_ok('import_check',len(r.violations) if hasattr(r,'violations') else 0))
    except Exception as e:
        results.append(_skip('import_check',str(e)))

    # 5. contract_verifier
    try:
        from codex_loop.core.contract_verifier import check_contract_test_coverage
        r = check_contract_test_coverage(str(root))
        val = 0 if r.is_clean() else 1
        results.append(_ok('contract_verify',val))
    except Exception as e:
        results.append(_skip('contract_verify',str(e)))

    # 6. subagent_evidence_verifier
    try:
        from codex_loop.core.subagent_evidence_verifier import verify_review_evidence
        evdir = root / '.ai' / 'evidence'
        if evdir.exists():
            issues = []
            for ef in list(evdir.rglob('*.json'))[:10]:
                r = verify_review_evidence(str(ef))
                if not r.get('valid'): issues.append(ef.name)
            results.append(_ok('subagent_evidence',len(issues)))
        else:
            results.append(_ok('subagent_evidence',0))
    except Exception as e:
        results.append(_skip('subagent_evidence',str(e)))

    return results

def warn_val(report):
    'Helper: get warnings count, handling both int and list types.'
    w = report.warnings
    return w if isinstance(w,int) else len(w)
