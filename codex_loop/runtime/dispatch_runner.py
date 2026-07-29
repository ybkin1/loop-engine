from pathlib import Path
from codex_loop.runtime.dispatcher import LoopDispatcher
from codex_loop.runtime.codex_agent_adapter import CodexAgentAdapter

class DispatchRunner:
    def __init__(self, project_root=None):
        self.root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
        self.dispatcher = LoopDispatcher()
        self.adapter = CodexAgentAdapter(self.root)
    def validate_manifest(self, manifest):
        valid, errors = manifest.validate()
        return valid, errors
    def prepare(self, manifest):
        ok, errors = self.validate_manifest(manifest)
        if not ok: raise ValueError(chr(59).join(errors))
        return self.dispatcher.prepare(manifest, self.adapter)
    def build_script(self, manifest):
        return self.dispatcher.build_execution_script(manifest, self.adapter)
    def finalize(self, manifest, batch_results):
        return self.dispatcher.finalize(manifest, batch_results)
    def get_spawn_specs(self, manifest):
        from codex_loop.runtime.agent_adapter import AgentInput
        specs = []
        for spec in manifest.subagents:
            inp = AgentInput(role_id=spec.subagent_id, task_id=manifest.parent_task_id, prompt=spec.prompt, input_files=list(spec.input_files))
            p = self.adapter.get_spawn_params(inp)
            specs.append(dict(id=spec.subagent_id, agent_type=p[chr(97)+chr(103)+chr(101)+chr(110)+chr(116)+chr(95)+chr(116)+chr(121)+chr(112)+chr(101)], message=p[chr(109)+chr(101)+chr(115)+chr(115)+chr(97)+chr(103)+chr(101)], fork_turns=p[chr(102)+chr(111)+chr(114)+chr(107)+chr(95)+chr(116)+chr(117)+chr(114)+chr(110)+chr(115)]))
        return specs