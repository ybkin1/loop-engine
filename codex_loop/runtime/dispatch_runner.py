"""DispatchRunner: connects LoopDispatcher -> CodexAgentAdapter -> spawn_agent"""
from pathlib import Path
from codex_loop.runtime.dispatcher import LoopDispatcher
from codex_loop.runtime.codex_agent_adapter import CodexAgentAdapter
from codex_loop.runtime.agent_adapter import AgentInput

class DispatchRunner:
    """End-to-end Loop dispatch: manifest -> plan -> spawn -> collect -> aggregate"""
    def __init__(self, project_root=None):
        self.root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
        self.dispatcher = LoopDispatcher()
        self.adapter = CodexAgentAdapter(self.root)

    def validate_manifest(self, manifest):
        """Validate manifest and check role contracts before dispatch."""
        valid, errors = manifest.validate()
        if not valid:
            return False, errors
        # Check each role contract exists
        for spec in manifest.subagents:
            role_dir = self.root / 'agents' / spec.role_hint.split('-')[0]
            if spec.role_hint and not role_dir.exists():
                errors.append(f{0}Role dir not found: {1}{2}.format(S,role_dir,S))
        return len(errors) == 0, errors

    def prepare(self, manifest):
        """Prepare execution plan from manifest. Returns ExecutionPlan or raises."""
        ok, errors = self.validate_manifest(manifest)
        if not ok:
            raise ValueError(f{0}Manifest validation failed: {1}{2}.format(S,chr(59).join(errors),S))
        plan = self.dispatcher.prepare(manifest, self.adapter)
        return plan

    def build_script(self, manifest):
        """Build executable script JSON for host orchestration."""
        return self.dispatcher.build_execution_script(manifest, self.adapter)

    def finalize(self, manifest, batch_results):
        """Generate aggregation prompt from batch results."""
        return self.dispatcher.finalize(manifest, batch_results)