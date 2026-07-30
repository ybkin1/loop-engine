import json,subprocess
from pathlib import Path

def check(project_root, evidence_path):
    r = subprocess.run([chr(34)+chr(103)+chr(105)+chr(116)+chr(34),chr(34)+chr(100)+chr(105)+chr(102)+chr(102)+chr(34),chr(34)+chr(45)+chr(45)+chr(110)+chr(97)+chr(109)+chr(101)+chr(45)+chr(111)+chr(110)+chr(108)+chr(121)+chr(34),chr(34)+chr(72)+chr(69)+chr(65)+chr(68)+chr(126)+chr(49)+chr(34)],capture_output=True,text=True,cwd=project_root)
    changed = set(f.strip() for f in r.stdout.splitlines() if f.strip())
    ep = Path(evidence_path)
    if not ep.exists(): return {chr(34)+chr(115)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115)+chr(34):chr(34)+chr(77)+chr(73)+chr(83)+chr(83)+chr(73)+chr(78)+chr(71)+chr(34),chr(34)+chr(99)+chr(104)+chr(97)+chr(110)+chr(103)+chr(101)+chr(100)+chr(34):sorted(changed)}
    try: ev = json.loads(ep.read_text())
    except: return {chr(34)+chr(115)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115)+chr(34):chr(34)+chr(73)+chr(78)+chr(86)+chr(65)+chr(76)+chr(73)+chr(68)+chr(34)}
    reviewed = set(ev.get(chr(34)+chr(102)+chr(105)+chr(108)+chr(101)+chr(115)+chr(95)+chr(114)+chr(101)+chr(118)+chr(105)+chr(101)+chr(119)+chr(101)+chr(100)+chr(34),[]))
    uncovered = changed - reviewed
    return {chr(34)+chr(115)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115)+chr(34):chr(34)+chr(80)+chr(65)+chr(83)+chr(83)+chr(34) if not uncovered else chr(34)+chr(85)+chr(78)+chr(67)+chr(79)+chr(86)+chr(69)+chr(82)+chr(69)+chr(68)+chr(34),chr(34)+chr(99)+chr(104)+chr(97)+chr(110)+chr(103)+chr(101)+chr(100)+chr(34):sorted(changed),chr(34)+chr(117)+chr(110)+chr(99)+chr(111)+chr(118)+chr(101)+chr(114)+chr(101)+chr(100)+chr(34):sorted(uncovered)}