# 设计：Agent Adapter 接口 + ZCode 实现桩

版本：v0.1 | 状态：candidate | 日期：2026-07-23

## 1. 问题

executor 当前直接调用 subprocess（`agents/<role>/run.py`）：
- 无抽象接口，无法支持多宿主
- 无 actor_id/session_id 记录
- 无法保证 developer != reviewer
- 不可用 → fixture 模拟（生产路径已禁止）

## 2. 设计

### 2.1 核心类型

```python
@dataclass
class AgentInput:
    role_id: str
    task_id: str
    prompt: str
    input_files: list[str]
    read_scope: list[str]
    write_scope: list[str]
    session_id: str | None
    def fingerprint(self) -> str: ...  # SHA256

@dataclass
class AgentOutput:
    actor_id: str
    session_id: str
    role_id: str
    task_id: str
    status: AgentStatus
    exit_code: int
    output_artifact: dict | None
    stdout: str; stderr: str
    start_time: str | None
    end_time: str | None
    input_fingerprint: str
    output_files: list[str]

class AgentStatus(str, Enum):
    PENDING, LAUNCHING, RUNNING, COMPLETED, FAILED, BLOCKED, UNAVAILABLE = ...
```

### 2.2 抽象接口

```python
class AgentAdapter(ABC):
    @abstractmethod
    def launch_agent(self, input: AgentInput) -> AgentOutput: ...
    @abstractmethod
    def get_status(self, session_id: str) -> AgentStatus: ...
    @abstractmethod
    def collect_output(self, session_id: str) -> AgentOutput: ...
    @property
    @abstractmethod
    def host_name(self) -> str: ...
```

### 2.3 ZCodeAgentAdapter（当前桩）

```python
class ZCodeAgentAdapter(AgentAdapter):
    host_name = "zcode"
    def launch_agent(self, input): raise AgentUnavailableError(...)
    def get_status(self, sid): return AgentStatus.UNAVAILABLE
    def collect_output(self, sid): raise AgentUnavailableError(...)
```

当前所有调用 → AgentUnavailableError → 上游转为 REAL_AGENT_UNAVAILABLE。

### 2.4 AgentUnavailableError

```python
class AgentUnavailableError(RuntimeError):
    """不可 fallback 到 fixture 模拟。"""
    def __init__(self, role_id, host, reason=""):
        super().__init__(
            f"REAL_AGENT_UNAVAILABLE: role='{role_id}' host='{host}'. {reason}"
        )
```

### 2.5 executor 集成

```python
class PhaseExecutor:
    def __init__(self, ..., agent_adapter: AgentAdapter | None = None):
        self._agent_adapter = agent_adapter
```

### 2.6 角色独立性验证

```python
assert dev_output.actor_id != reviewer_output.actor_id
assert dev_output.session_id != reviewer_output.session_id
```

## 3. 测试

- AgentInput.fingerprint() 稳定性
- AgentUnavailableError 上抛链路
- Mock adapter 正常流程
- executor + adapter 联合行为
