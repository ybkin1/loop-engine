# T-0036 独立评审 Changed-Path Manifest v0.1

## Execution boundary

本 manifest 只记录 G-T-0036-FRESH-INDEPENDENT-REVIEW-V0-1 的实际评审执行范围。评审者为全新只读 auditor；冻结对象和历史 T-0036 证据保持不变。本 manifest 自身不纳入自身 SHA-256 指纹，避免自引用。

## Paths created by this execution

- .ai/evidence/T-0036/material-library-independent-review.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-commands.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-validation.v0.1.md
- .ai/evidence/T-0036/material-library-independent-review-changed-path-manifest.v0.1.md

### Created file fingerprints

- path: .ai/evidence/T-0036/material-library-independent-review.v0.1.md
  size: 8639
  sha256: 805441888530854A04AE6E228B0BACC83A5184945F59FC2CE80EB10E81234186
- path: .ai/evidence/T-0036/material-library-independent-review-commands.v0.1.md
  size: 2513
  sha256: CD6CCEB6979907EF4D4AE580C8DAB365DE2953C5D970B70D50E982BE9D4E707E
- path: .ai/evidence/T-0036/material-library-independent-review-validation.v0.1.md
  size: 1868
  sha256: 8AAB281F5C1D9828253CD64D3F27171CB625D2FA0CCCD9B819FB91D82FE5B4AD

## Governance paths updated

- .ai/gates.yaml：记录用户批准、后续精确执行请求、fresh reviewer 身份、REPAIR_REQUIRED verdict 和证据指针。
- .ai/state.yaml：记录当前 review checkpoint、冻结输入未漂移和未授权的后续边界。
- .ai/HANDOFF.md：记录评审结果、发现、验证状态、阻断边界和下一安全动作。

## Protected paths checked

- 冻结清单列出的 58 个 T-0036 输入：评审前后相对路径、字节数和 SHA-256 均一致。
- materials/catalog.yaml、material-schema.yaml、source-register.md、coverage-matrix.md、templates、frameworks、profiles：未修改。
- .ai/evidence/T-0036 中既有 source-validation、coverage-matrix、simulation、completion package 和登记证据：未修改。
- .ai/tasks/T-0036.md、.ai/DECISIONS.md：本次 review execution 未修改。
- T-0037 源码、测试、文档和证据：未修改。
- 全局 Codex、AGENTS.md、skill、MCP、plugin、automation、hook、protocol、部署、数据库、权限、密钥、支付、生产数据、迁移和外部业务项目：未触碰。

当前结论：scope-contained / frozen-inputs-preserved / review-evidence-recorded / repair-required
