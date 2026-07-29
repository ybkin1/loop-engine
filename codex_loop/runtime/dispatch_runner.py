"""DispatchRunner: connects LoopDispatcher -> CodexAgentAdapter -> spawn_agent"""
from pathlib import Path

from codex_loop.runtime.codex_agent_adapter import CodexAgentAdapter
from codex_loop.runtime.dispatcher import LoopDispatcher


class DispatchRunner:
    """End-to-end Loop dispatch: manifest -> plan -> spawn -> collect -> aggregate"""
    def __init__(self, project_root=None):
        self.root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
        self.dispatcher = LoopDispatcher()
        self.adapter = CodexAgentAdapter(self.root)

    def validate_manifest(self, manifest):
        valid, errors = manifest.validate()
        if not valid:
            return False, errors
        for spec in manifest.subagents:
            if spec.role_hint:
                role_dir = self.root / 'agents' / spec.role_hint
                if not role_dir.exists():
                    errors.append('Role dir not found: ' + str(role_dir))
        return len(errors) == 0, errors

    def prepare(self, manifest):
        ok, errors = self.validate_manifest(manifest)
        if not ok:
            raise ValueError('Manifest validation failed: ' + '; '.join(errors))
        return self.dispatcher.prepare(manifest, self.adapter)

    def get_spawn_specs(self, manifest):
        """Generate spawn_agent call specs for each sub-agent."""
        specs = []
        for spec in manifest.subagents:
            from codex_loop.runtime.agent_adapter import AgentInput
            inp = AgentInput(role_id=spec.subagent_id, task_id=manifest.parent_task_id, prompt=spec.prompt, input_files=list(spec.input_files))
            params = self.adapter.get_spawn_params(inp)
            specs.append({'id': spec.subagent_id,'agent_type': params['agent_type'],'message': params['message'],'fork_turns': params['fork_turns']})
        return specs
    def build_script(self, manifest):
        return self.dispatcher.build_execution_script(manifest, self.adapter)

    def finalize(self, manifest, batch_results):
        return self.dispatcher.finalize(manifest, batch_results)
