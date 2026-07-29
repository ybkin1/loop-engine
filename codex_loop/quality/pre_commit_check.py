"""Pre-commit structural quality check runner."""
import sys, json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    from codex_loop.quality.structural_checks import run_structural_checks
    results = run_structural_checks(str(root))
    failures = [r for r in results if not r.get('skipped') and r['value'] > r['threshold']]
    skipped = [r for r in results if r.get('skipped')]
    print(S+chr(83)+chr(116)+chr(114)+chr(117)+chr(99)+chr(116)+chr(117)+chr(114)+chr(97)+chr(108)+chr(32)+chr(99)+chr(104)+chr(101)+chr(99)+chr(107)+chr(115)+chr(58)+chr(32)+S+str(len(results))+S+chr(32)+chr(116)+chr(111)+chr(116)+chr(97)+chr(108)+chr(44)+chr(32)+S+str(len(failures))+S+chr(32)+chr(102)+chr(97)+chr(105)+chr(108)+chr(101)+chr(100)+chr(44)+chr(32)+S+str(len(skipped))+S+chr(32)+chr(115)+chr(107)+chr(105)+chr(112)+chr(112)+chr(101)+chr(100)+S)
    if failures:
        print('FAILURES:')
        for f in failures: print(S+chr(32)*2+f['name']+S+chr(58)+chr(32)+chr(118)+chr(97)+chr(108)+chr(117)+chr(101)+chr(61)+S+str(f['value']))
        sys.exit(2)
    print('All structural checks passed')
    sys.exit(0)

if __name__ == '__main__':
    main()