# T-0036 素材库版本冻结 Gate 范围 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

## 注册阶段 allowlist

1. `.ai/evidence/T-0036/material-library-version-freeze-gate-request.v0.1.md`
2. `.ai/evidence/T-0036/material-library-version-freeze-decision-packet.v0.1.md`
3. `.ai/evidence/T-0036/material-library-version-freeze-changed-path-baseline.v0.1.md`
4. `.ai/evidence/T-0036/material-library-version-freeze-registration-commands.v0.1.md`
5. `.ai/evidence/T-0036/material-library-version-freeze-scope.v0.1.md`
6. `.ai/gates.yaml`
7. `.ai/state.yaml`
8. `.ai/HANDOFF.md`

## 批准后且收到单独精确执行请求的 allowlist

1. `.ai/evidence/T-0036/material-library-version-freeze-record.v0.1.md`
2. `.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md`
3. `.ai/evidence/T-0036/material-library-version-freeze-validation.v0.1.md`
4. `.ai/evidence/T-0036/material-library-version-freeze-changed-path-manifest.v0.1.md`
5. `.ai/gates.yaml`
6. `.ai/state.yaml`
7. `.ai/HANDOFF.md`

批准不等于执行。执行阶段 allowlist 只有在 Gate 已由用户明确批准且之后收到精确执行短语时生效。

## 内容快照边界

- 冻结对象仅为 residual-path-repair freeze manifest 中的 65 个已接受素材库 subject。
- 最终 version-freeze manifest 必须新增，不得覆盖旧 freeze manifest，并严格复现 65/65 path、size、SHA-256。
- decision record、review evidence、candidate-path gap、治理文件和 Gate 证据不纳入素材内容快照。
- isolated candidate-path gap 保持开放、明确记录且未被豁免。

## 禁止路径与效果

- 禁止修改 65 个素材对象、旧 freeze manifest、catalog、register、profiles、templates 或既有 review evidence。
- 禁止修改 candidate/global Project Governor、测试、`codex_loop` 或 Runtime。
- 禁止冻结 isolated candidate、Runtime、Agent、Host 或真实项目行为。
- 禁止关闭 T-0036，禁止创建或执行 T-0037 review，禁止进入 Host Integration。
- 禁止部署、迁移、权限、密钥、生产数据或真实项目动作。
- 禁止使用 Git tag、commit 或发布动作替代版本冻结证据。

## 验证与恢复

- 冻结执行前后均验证 `65/65` path、size、SHA-256；任一漂移立即 `BLOCKED`。
- 比较新旧 freeze manifest，证明内容三元组完全一致；验证 `research-baseline-v0.1` 身份一致。
- 运行 `validate_state.py`、`audit_handoff.py`、`git diff --check`。
- 执行 changed-path manifest 必须严格落在执行 allowlist；越界立即 `SCOPE_VIOLATION`。
- 保留全部 preimage、部分增量证据和无关工作树变更；不得自动删除、reset、checkout 或静默 rebaseline。
- 失败时停止、记录实际状态和漂移/越界详情；修复、破坏性恢复或扩展范围均需新的明确 Gate。
