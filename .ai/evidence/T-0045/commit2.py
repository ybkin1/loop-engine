import subprocess
ROOT = r'C:\Users\Administrator\ZCodeProject\loop-engine'
files = [f'tools/tool_{n}.py' for n in ['route_intent','constraint_check','execute_phase','execution_log','veto_escalate','evidence_submit','handoff','load_context']] + ['tools/server.py']
subprocess.run(f"git add -- {' '.join(files)}", cwd=ROOT, shell=True, check=True)
msg = "v3.5: MCP tools — route_intent + constraint_check + execute_phase + execution_log + veto_escalate + evidence_submit + handoff + load_context (20 total)"
r = subprocess.run(f'git commit -m "{msg}"', cwd=ROOT, shell=True, capture_output=True, text=True)
print(r.stdout or r.stderr)
subprocess.run("git log --oneline -3", cwd=ROOT, shell=True)
