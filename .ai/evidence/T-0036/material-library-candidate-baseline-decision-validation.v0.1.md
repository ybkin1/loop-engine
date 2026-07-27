# T-0036 候选素材基线决策验证 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

Decision: `accepted_candidate_baseline`

## Validation Scope

本验证只确认用户接受记录、Gate 状态投影、候选身份、唯一冻结证据基线和禁止下游边界；不执行版本冻结、T-0036 closeout、T-0037 review 或任何 Runtime/Agent/Host Integration 动作。

| assertion | result | observed |
| --- | --- | --- |
| explicit user decision | PASS | exact phrase `接受 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`; actor `user` |
| candidate identity | PASS | `candidate / research-baseline-v0.1` |
| only evidence baseline | PASS | residual-path-repair freeze manifest; 65 subjects; SHA-256 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |
| frozen subjects | PASS | `65/65`, zero drift |
| T-0036 status | PASS | `active`; candidate baseline accepted; not closed |
| version freeze | PASS | not authorized by this decision |
| T-0037 review | PASS | not created or executed by this decision |
| downstream boundaries | PASS | Host Integration, Runtime, Agent, installation, activation, and real-project entry remain unauthorized |

## Command Results

| command | exit | result |
| --- | ---: | --- |
| `validate_state.py` | 0 | state usable |
| `audit_handoff.py` | 0 | handoff audit passed |
| `git diff --check` | 0 | no output |

冻结清单独立复核：manifest `9835` bytes / SHA-256 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`；declared/parsed/matched=`65/65/65`；mismatches=`0`。

验证结论：本次仅记录用户候选基线接受；没有版本冻结、T-0036 closeout、T-0037 review、Runtime、Agent、Host Integration、安装、激活或真实项目动作。
