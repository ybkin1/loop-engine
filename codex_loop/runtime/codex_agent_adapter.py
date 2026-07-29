"""CodexAgentAdapter -- Agent launching via Codex multi_agent_v1_spawn_agent."""
from __future__ import annotations
from pathlib import Path
from codex_loop.runtime.agent_adapter import AgentAdapter,AgentInput,AgentOutput,AgentStatus,AgentUnavailableError

class CodexAgentAdapter(AgentAdapter):
    """Codex native agent adapter. Pre-launch validation + spawn parameter generation."""
    host_name = 'codex'
    ROLE_TO_AGENT_TYPE = {
        'product-manager': 'researcher',
        'system-architect': 'designer-agent',
        'module-architect': 'designer-agent',
        'developer': 'code-agent',
        'quality-engineer': 'test-reviewer',
        'security-engineer': 'explorer',
        'independent-reviewer': 'code-reviewer',
        'delivery-manager': 'default',
        'release-engineer': 'default',
        'project-manager': 'default',
    }

    def __init__(self, project_root=None):
        self._project_root = Path(project_root) if project_root else None

    def prepare_launch(self, agent_input):
        """Assign session/actor IDs and freeze input fingerprint."""
        import uuid, datetime
        agent_input.session_id = agent_input.session_id or 'codex-sess-' + str(uuid.uuid4())[:8]
        agent_input.actor_id = agent_input.actor_id or 'codex-actor-' + agent_input.role_id
        agent_input.start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return agent_input

    def collect_result(self, agent_input, raw_output):
        """Build AgentOutput from raw agent output."""
        import datetime
        out = raw_output if isinstance(raw_output, str) else str(raw_output)
        return AgentOutput(
            actor_id=agent_input.actor_id or 'unknown',
            session_id=agent_input.session_id or 'unknown',
            role_id=agent_input.role_id,
            task_id=agent_input.task_id,
            status=AgentStatus.COMPLETED,
            stdout=out,
            start_time=agent_input.start_time,
            end_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            input_fingerprint=agent_input.fingerprint(),
        )

    ROLE_FORK_POLICY = {
        'independent-reviewer': 'none',  # fresh context for unbiased review
        'product-manager': 'none',       # only sees requirements
        'project-manager': 'none',       # only sees task graph
        'delivery-manager': 'none',       # only sees delivery packet
    }

    def get_spawn_params(self, agent_input):
        """Return Codex spawn_agent params with role-appropriate fork_turns.

        Roles needing code context (developer,test-engineer,quality-engineer,
        security-engineer,system-architect,module-architect,release-engineer)
        get fork_turns=chr(39)+chr(97)+chr(108)+chr(108)+chr(39)+chr(32)+chr(35)+chr(32)+chr(102)+chr(117)+chr(108)+chr(108)+chr(32)+chr(99)+chr(111)+chr(100)+chr(101)+chr(32)+chr(99)+chr(111)+chr(110)+chr(116)+chr(101)+chr(120)+chr(116).
        Review/management roles get fork_turns=chr(39)+chr(110)+chr(111)+chr(110)+chr(101)+chr(39)+chr(32)+chr(35)+chr(32)+chr(102)+chr(114)+chr(101)+chr(115)+chr(104)+chr(32)+chr(112)+chr(101)+chr(114)+chr(115)+chr(112)+chr(101)+chr(99)+chr(116)+chr(105)+chr(118)+chr(101).
        """
        atype = self.ROLE_TO_AGENT_TYPE.get(agent_input.role_id, 'default')
        fork = self.ROLE_FORK_POLICY.get(agent_input.role_id, 'all')
        return {'agent_type': atype, 'message': agent_input.prompt, 'fork_turns': fork}

    def launch_agent(self, agent_input):
        inp = self.prepare_launch(agent_input)
        return AgentOutput(
            actor_id=inp.actor_id or 'unknown',
            session_id=inp.session_id or 'unknown',
            role_id=inp.role_id,
            task_id=inp.task_id,
            status=AgentStatus.LAUNCHING,
            input_fingerprint=inp.fingerprint(),
        )

    def get_status(self, session_id):
        return AgentStatus.RUNNING

    def collect_output(self, session_id):
        raise AgentUnavailableError('unknown', self.host_name, 'Use wait_agent to collect results.')