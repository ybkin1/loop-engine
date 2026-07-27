# T-0036 Path-Closure Fresh Rereview Commands v0.1

Working directory: `C:\Users\Administrator\.codex\loop-engine-lab`

All commands were read-only except the final `apply_patch` writes to the four authorized evidence paths. No temporary file was created.

## Startup And Gate Checks

```powershell
Get-Content -Raw 'C:\Users\Administrator\.codex\skills\project-governor\SKILL.md'
Get-Content -Raw 'AGENTS.md'
Get-Content -Raw '.ai/state.yaml'
Get-Content -Raw '.ai/HANDOFF.md'
Get-Content -Raw '.ai/tasks/T-0036.md'
Get-Content -Raw '.ai/gates.yaml'
Get-Content -Raw '.ai/task_graph.yaml'
Get-Content -Raw '.ai/evidence/T-0036/material-library-path-rereview-gate-request.v0.1.md'
Get-Content -Raw '.ai/evidence/T-0036/material-library-path-rereview-control-manifest.v0.1.md'
Get-Content -Raw '.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md'
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Key result: target Gate count `1`, `status=approved`, `execution_status=review_in_progress`, `current_gate_id=null`, pending Gate count `0`; startup validator exit `0`, `[ok] state is usable`.

## Freeze And Control Pre/Post Check

The inline Python check parsed each manifest triple, read every subject byte-for-byte, and compared path, byte size, and full SHA-256:

```powershell
@'
from pathlib import Path
import hashlib,re,sys
r=Path.cwd()
m=r/'.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md'
c=r/'.ai/evidence/T-0036/material-library-path-rereview-control-manifest.v0.1.md'
b=m.read_bytes(); t=b.decode('utf-8')
rows=re.findall(r'^- path: (.+)\r?\n  size: (\d+)\r?\n  sha256: ([0-9A-F]{64})$',t,re.M)
bad=[]
for p,s,h in rows:
    q=r/p
    if not q.is_file(): bad.append((p,'absent')); continue
    x=q.read_bytes(); a=hashlib.sha256(x).hexdigest().upper()
    if len(x)!=int(s) or a!=h: bad.append((p,len(x),a,s,h))
cb=c.read_bytes()
print(len(rows),len(set(p for p,_,_ in rows)),len(bad),len(b),hashlib.sha256(b).hexdigest().upper(),len(cb),hashlib.sha256(cb).hexdigest().upper())
sys.exit(bool(bad) or len(rows)!=65 or len(set(p for p,_,_ in rows))!=65)
'@ | python -
```

Pre and post key stdout: `65 65 0 9835 DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC 4760 65D1D9EF4F98CD73A68AAE3E6119D62B08EEA8A91811A8FB888DBF693C70876B`; exit `0`.

## Independent YAML, Markdown, Reference, Set, And Freshness Check

The successful inline checker used PyYAML for all frozen YAML and structural Markdown parsing for headings, tables, links, and fenced-block balance. It independently asserted F-001..F-006, exact duplicate sets, catalog local references, profile/phase/selection closure, strict subsets, freshness invariants, and governance boundaries.

```powershell
@'
from pathlib import Path
from collections import Counter
from datetime import datetime
import re,sys,yaml
R=Path.cwd(); failures=[]
def check(name, value, detail):
    print(('PASS' if value else 'FAIL'),name,detail)
    if not value: failures.append(name)
f=(R/'.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md').read_text(encoding='utf-8')
paths=[x[0] for x in re.findall(r'^- path: (.+)\r?\n  size: (\d+)\r?\n  sha256: ([0-9A-F]{64})$',f,re.M)]
ys=[p for p in paths if p.endswith(('.yaml','.yml'))]; ms=[p for p in paths if p.endswith('.md')]
for p in ys: yaml.safe_load((R/p).read_text(encoding='utf-8'))
check('parse.yaml',len(ys)==21,'21/21')
check('parse.markdown',len(ms)==43 and all((R/p).read_text(encoding='utf-8').count('```')%2==0 for p in ms),'43/43')
C=yaml.safe_load((R/'materials/catalog.yaml').read_text(encoding='utf-8')); S=yaml.safe_load((R/'materials/material-schema.yaml').read_text(encoding='utf-8'))
G=yaml.safe_load((R/'materials/source-register.yaml').read_text(encoding='utf-8')); GS=yaml.safe_load((R/'materials/source-register-schema.yaml').read_text(encoding='utf-8'))
MD=(R/'materials/source-register.md').read_text(encoding='utf-8'); CV=(R/'materials/coverage-matrix.md').read_text(encoding='utf-8')
PJ=yaml.safe_load((R/'.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml').read_text(encoding='utf-8')); SL=yaml.safe_load((R/'.ai/evidence/T-0036/simulation/material-selection.v0.1.yaml').read_text(encoding='utf-8')); PH=yaml.safe_load((R/'.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml').read_text(encoding='utf-8'))
cm=C['materials']; gr=G['records']; ci=[x['material_id'] for x in cm]; ri=[x['material_id'] for x in gr]; bc={x['material_id']:x for x in cm}; br={x['material_id']:x for x in gr}
auth={x.strip(' 。') for x in S['fields']['authority'].split('|')}; stype={x.strip(' 。') for x in S['fields']['source_type'].split('|')}
check('F-001',len(cm)==46 and all(all(k in x and x[k] not in (None,'',[]) for k in S['required']) for x in cm) and all(x['authority'] in auth and x['source_type'] in stype for x in cm),'46 records / 17 fields / 0 enum violations')
rows=[]
for line in MD.splitlines():
    cells=[x.strip() for x in line.strip().strip('|').split('|')]
    if cells and re.fullmatch(r'[A-Z]+(?:-[A-Z]+)*-\d{3}',cells[0]): rows.append(cells)
pi=[x[0] for x in rows]; bp={x[0]:x for x in rows}
check('F-002',set(ci)==set(ri)==set(pi) and len(set(ci))==46 and max(Counter(ci).values())==max(Counter(ri).values())==max(Counter(pi).values())==1 and all(bc[i]['verification_status']==br[i]['verification_status']==bp[i][7] for i in ci),'46/46/46 / duplicates 0 / conflicts 0')
packets={x['phase_id']:x['human_decision']['evidence_packet'] for x in PH['phases']}
closure=PJ['project_profile_id']==SL['project_profile_id']==PH['project_profile_id'] and PJ['project_selection_id']==SL['parent_selection_id'] and PJ['phase_profile']==SL['phase_profile_id']==PH['phase_profile_id'] and SL['selection_id']==PH['material_selection_id']
check('F-003',closure and len(PH['phases'])==11 and all((R/p).is_file() for p in packets.values()) and packets['P1-P2']=='materials/material-library-review-packet.md','11 phases / path closure')
mentions=[]
for p,a,b in re.findall(r'\b([A-Z]+(?:-[A-Z]+)*)-(\d{3})(?:\.\.(\d{3}))?',CV.split('## 待补素材队列',1)[0]): mentions += [f'{p}-{n:03d}' for n in range(int(a),int(b)+1)] if b else [f'{p}-{a}']
over={k:v for k,v in Counter(mentions).items() if v>1}
check('F-004',set(mentions)==set(ci) and set(over)=={'SEC-004','OPS-003'},'46/46 / intended overlaps only')
pm=set(PJ['selected_materials']); sm={x['material_id'] for x in SL['selected_materials']}; pt=set(PJ['selected_templates']); st=set(SL['selected_templates'])
check('F-005',SL['subset_relation']=='strict_subset' and sm<pm and (len(sm),len(pm))==(8,17) and st<pt and (len(st),len(pt))==(7,9) and all((R/p).is_file() for p in pt|st) and 'materials/profiles/material-selection-record.yaml' in pt,'8/17 and 7/9 / paths closed')
start=datetime.fromisoformat(G['retrieval_run']['started_at']); end=datetime.fromisoformat(G['retrieval_run']['completed_at']); inv=[]
for x in gr:
    try: dt=datetime.fromisoformat(x['retrieved_at']); assert dt.utcoffset() is not None and start<=dt<=end
    except Exception: inv.append((x['material_id'],'time'))
    if any(k not in x or x[k] in ('',[]) or (x[k] is None and k!='http_status') for k in GS['required']): inv.append((x['material_id'],'required'))
    if x['access_method']=='local_file' and (x['http_status'] is not None or x['final_url']!='not_applicable'): inv.append((x['material_id'],'local'))
    if x['access_method']=='http_get' and x['verification_status']=='content_read' and not (isinstance(x['http_status'],int) and 200<=x['http_status']<400 and x['page_title']!='not_observed' and x['failure_reason']=='none'): inv.append((x['material_id'],'read'))
check('F-006',not inv and all(bc[i]['source_observation']==br[i]['source_observation'] for i in ci),'46/46 / invariants 0')
check('boundaries',PH['simulation_only'] is True and PH['planned_not_executed'] is True and 'baseline_not_accepted' in (R/'materials/material-library-review-packet.md').read_text(encoding='utf-8'),'simulation/planned/non-acceptance explicit')
print('SUMMARY',len(failures),'failures'); sys.exit(bool(failures))
'@ | python -
```

The actually executed final inline checker exited `0` with `14/14 PASS`. Three earlier authoring iterations exited `1` because the reviewer script used the wrong simulation graph key, then over-constrained the user-decision node, then applied an HTTP-only invariant to local records. These were checker-authoring errors, not candidate failures; they created or modified no file and were corrected before the final required check.

Final key stdout: YAML `21/21`; Markdown `43/43`; F-001..F-006 PASS; catalog/register/Markdown `46/46/46`; coverage `46/46`; materials `8/17`; templates `7/9`; freshness `46/46`; summary `14/14 PASS`; exit `0`.

## Required Validator And Tests

```powershell
python .ai/evidence/T-0036/material-library-repair-validator.v0.1.py C:\Users\Administrator\.codex\loop-engine-lab
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='-p no:cacheprovider'
python -m pytest tests/codex_loop -q
python -m pytest -q
```

- Repair validator: exit `0`; `catalog=46`, `authority_violations=0`, `register=46/46`, `status_conflicts=0`, `markdown_ids=46`, `coverage=46/46`, `freshness=46/46`, `phase_profile_ref=1/1`, `selection_materials=8/17`, `selection_templates=7/9`, `PASS`.
- Focused tests: exit `0`; `28 passed in 1.62s`.
- Full tests: exit `0`; `41 passed, 5 subtests passed in 7.60s`.
- Existing cache pre/post composite: `36` files / `08F305340AE17A3311304A8B2C8B7378E846CC108098FC907439365A752D37CD`; unchanged, so no `.pytest_cache` or `__pycache__` write occurred.

## Governor, Handoff, And Diff

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
git diff --check
```

- `validate_state.py`: exit `0`; `[ok] state is usable`.
- `audit_handoff.py`: exit `0`; `[ok] handoff audit passed`.
- `git diff --check`: exit `0`; no stdout.
