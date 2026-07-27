# T-0036 独立评审冻结清单 v0.1

## 冻结目的

本清单冻结 T-0036 当前候选素材库及其已完成交付/模拟证据，作为后续全新独立、只读评审的唯一内容输入。冻结不代表候选基线已被接受，也不代表版本已最终冻结。

冻结时间：2026-07-23T15:37:40+08:00

## 冻结规则

- 共冻结 58 个文件；每个文件按相对路径、字节数和完整 SHA-256 校验。
- 评审开始前和评审完成后都必须重新核对全部 58 个对象；任一不一致即停止并记录 BLOCKED。
- 本清单、独立评审 Gate 请求、登记命令、未来独立评审输出和治理投影文件不属于冻结内容对象。
- 冻结对象只读；不得修改、删除、重命名、规范化或追加内容。
- 评审 verdict 只属于证据，不得直接转化为修复、复审、候选基线接受、版本冻结或 T-0037 评审许可。

## Frozen subjects

- path: .ai/evidence/T-0036/commands.md
  size: 2617
  sha256: EAA67CDE1BDB4DAFBE2BEA1196068D39B554C10FC9FAC042C27AEFBAD11C468F
- path: .ai/evidence/T-0036/coverage-matrix.v0.1.md
  size: 1019
  sha256: 3A399C0F6164B3F00A91AC9E747D758B20A88469D495C9F0438945287F299F2E
- path: .ai/evidence/T-0036/material-library-completion-changed-path-manifest.v0.1.md
  size: 2092
  sha256: 324BECFD5263A9B373CD0FAC2CC3BE046CE3CF3FA4B6306AE5C85EE9ABFB3CAC
- path: .ai/evidence/T-0036/material-library-completion-gate-approval-record.v0.1.md
  size: 725
  sha256: 52E549CC6ED48C7AEEB92B5A08CA2C3155286AB343249F325805E971F759CD52
- path: .ai/evidence/T-0036/material-library-completion-gate-request.v0.1.md
  size: 4140
  sha256: 4197B54835237A0F6151B94D51E262C1DA120D6B2FAC9BB1EBF62F587DF3C795
- path: .ai/evidence/T-0036/material-library-completion-validation.v0.1.md
  size: 3274
  sha256: 2EE186860313C3FAC77C37182D868A0D70DBDF45775B34B316C7AF3A909C4115
- path: .ai/evidence/T-0036/simulation/architecture-baseline.v0.1.md
  size: 5184
  sha256: D44757B943197FF9F32C8A27DA8660884F52A84F3A532DD732759657896E82EF
- path: .ai/evidence/T-0036/simulation/human-review-packet.v0.1.md
  size: 2524
  sha256: 6232D0C65C5BA5606C470E834328021C78BBDE5085A6B718A3A93A02ADE48919
- path: .ai/evidence/T-0036/simulation/loop-simulation-plan.v0.1.md
  size: 6580
  sha256: 22470AACE829F9D26E594C51833CA0763F3304C98338B453E0D08A1F1D4878A4
- path: .ai/evidence/T-0036/simulation/material-selection.v0.1.yaml
  size: 4518
  sha256: 76AD8F9A563E2CFF088DE701AF3084B75F93121F8967B3860266ABD91916CEC2
- path: .ai/evidence/T-0036/simulation/project-profile.v0.1.yaml
  size: 1728
  sha256: 03D29A11A9C1C990B778CC1B2B8E6180889C2A3049BA04E05F56C72B0023D33B
- path: .ai/evidence/T-0036/simulation/quality-profile.v0.1.yaml
  size: 1484
  sha256: 8F65C10188E51B06D6F67E0EA304B8A07D76A0E208EF512AA1824671C6093A81
- path: .ai/evidence/T-0036/simulation/role-roster.v0.1.yaml
  size: 12326
  sha256: 938018DE594695096D7FCA002595A74B786857A0B03343BF055700A4647ECD70
- path: .ai/evidence/T-0036/simulation/simulated-run-summary.v0.1.md
  size: 2853
  sha256: 222F101763736B3CC93BC54E069339197D83ED17B4BC1014EA7C69D622CBC5A8
- path: .ai/evidence/T-0036/simulation/simulation-architecture-decisions.v0.1.md
  size: 2220
  sha256: 347FD55720A95FF589637B4DCB188A61D0F15F75D2B30482046549694C909860
- path: .ai/evidence/T-0036/simulation/simulation-validation.v0.1.md
  size: 1016
  sha256: 6F8AC15EF157B584D88722367BD6D2DA92C9A4B93B15165327F5FA79056B9670
- path: .ai/evidence/T-0036/simulation/task-graph.v0.1.yaml
  size: 9192
  sha256: 0B186FF79EE6BCC66522C7C15C75B9B971E2FD33FA7D95CC3BBE56A0FB4EBC68
- path: .ai/evidence/T-0036/source-validation.v0.1.md
  size: 1498
  sha256: 60E012CFDBB2CA9C0CC3074ABCDAE5D70EA02C6561815DF22E371AF4C7E872C6
- path: materials/README.md
  size: 2983
  sha256: 9D8E7BFD1CE594AD4E49BFEFCE901DE098CAE5C9D6A6DBC270B0FFAD5E6EC372
- path: materials/catalog.yaml
  size: 53145
  sha256: B8F2675C4C6E1D41BCC67A542304A9DD1C9CE2D7A5DF322C91A849C694D34C7F
- path: materials/coverage-duplication-review.md
  size: 4231
  sha256: 634FE5CBA4AEF01CA48E3A2B8B9253BE8C7F23E3CD23D0531BCC91AB36204B0B
- path: materials/coverage-matrix.md
  size: 3377
  sha256: D210B5B19B2573A90431C62A20948F9B07CAF7D32762294AA68BFE764B6F18B6
- path: materials/frameworks/composition-rules.md
  size: 1328
  sha256: EF0036AF0B6DADD74D7AD8A486BA95D46B2670540D701E627F747BF302110516
- path: materials/frameworks/prompt-and-agent-evaluation.md
  size: 1311
  sha256: 1381B04A3377D4677BC53D32B824CE899240F134BC8EE92742780B4BAD7514FC
- path: materials/frameworks/source-to-loop-mapping.md
  size: 1373
  sha256: 80935810C4902891B71CEF0E32B3A7231358F3CC48C28DBE43131FE5DA6EA941
- path: materials/material-library-review-packet.md
  size: 7483
  sha256: 0ABBE5FE66A1C587D9DAC19C0A437A2C94EB60CA3B34FF8860FA924869F606ED
- path: materials/material-schema.yaml
  size: 1847
  sha256: 775D49F272CC3E62B749D2D3DF8831820239DE5062294927028BFC0BA5235360
- path: materials/profiles/material-selection-record.yaml
  size: 829
  sha256: 8A45CA458D6CE935253E7F602FBDA373EE9E441F57CAA34825F579557E43FED9
- path: materials/profiles/project-profile.yaml
  size: 826
  sha256: 4F3F30BA67E862D2D0F669B634CB62DC07BB0A63BD0909C8319C01E18F6A6B1E
- path: materials/source-register.md
  size: 5760
  sha256: 599A96F287CE87CF72A709AE6D853F4FE602B9E154292CC2C750E0E9A91FECBB
- path: materials/templates/acceptance-matrix.yaml
  size: 304
  sha256: AE94CEFC389E563FF217C1416FE33FEB21DD837920B95077A82895D336B7A911
- path: materials/templates/adr.md
  size: 447
  sha256: F60EBFAFA8436AE142A61C83202ACE5630DFD26CA985A5EBC5476BEEDD6C829F
- path: materials/templates/agent-run-envelope.yaml
  size: 689
  sha256: F639A57C80C1991E5D5EAB2A8DB0915FDA798A4B639E87CDA8585A2D0ECF4DE7
- path: materials/templates/api-contract.yaml
  size: 607
  sha256: 10AC7005067B97FCD9CF4A4EF0CD9AFBCF00AB1A252AF7E58AB94BB6906C6DA0
- path: materials/templates/architecture-description.md
  size: 854
  sha256: 7C1C3A1ADFA8FC66BF571BCB0C470197E2F91A7F3AFBCC869E3503AFF10202F5
- path: materials/templates/change-record.md
  size: 320
  sha256: F23BE41384CF17B153EC1ABC3F21891F952F60EFCF0A6790761F4C9775630683
- path: materials/templates/deployment-plan.md
  size: 612
  sha256: 80CB0B9DDCE5272E180FF7E65281ECF7E3A556D0E3FD5F197078762C40DDD49A
- path: materials/templates/feedback-record.yaml
  size: 486
  sha256: 97E89D4CC65A0E13065C2C416E8209901F738BD02122A8950627FC6F94211E11
- path: materials/templates/host-adapter-contract.md
  size: 738
  sha256: 0EF2ECA22292BD8B9C84A7AC98F9DFD46E67ABE796A0983BEFA8A49BE28259F7
- path: materials/templates/human-review-packet.md
  size: 701
  sha256: EE7FF76F6061C563D51A3AB13F34EEC30714CEC674C52E7E4C8D2B5BD65FDFDD
- path: materials/templates/independent-review.md
  size: 676
  sha256: A0EE5F07EA7D62291B47CB7C83B72588574913D27F6268CCAA2337B78437AA9A
- path: materials/templates/metrics-plan.md
  size: 357
  sha256: 2DEB80D4C362DE04AAEF3C3ADF474EF60EE13D3C1DC641CC4EF4BBB18FA75678
- path: materials/templates/observability-plan.md
  size: 428
  sha256: AFB8021E4E35FEF7E0F2311C8C95618FDB36277590DC4888F0E30194A7EDD3A2
- path: materials/templates/performance-plan.md
  size: 388
  sha256: 012829B380AACFA7B62D1D8BFAA1FF33A8E1E1D2D3E0EE679EB1D0EACC08C4A6
- path: materials/templates/phase-profile.yaml
  size: 734
  sha256: E1E7839FA997066FE4AD64BFDA3BF255427CE99647D8D972FE9E9993703F5A57
- path: materials/templates/project-plan.md
  size: 561
  sha256: 3FE4BD925A8BA44C7922BDA4F2A183AD2CF923D71DA145B10A6538A93D49E1A6
- path: materials/templates/prompt-contract.md
  size: 829
  sha256: 866C34DBAD3F5F0B9196A2235B40007C3C143EFE7C8066865166EC2C5ED0D390
- path: materials/templates/quality-profile.yaml
  size: 675
  sha256: 37863A515EA66C9D658ECF8B5D1C95FA81CDBD6C780F823BED27191BE3F8235C
- path: materials/templates/release-readiness.md
  size: 839
  sha256: 00C9413C140AD98232133B83045EB5F95492876D6A55B282E86AE417DEB4FBB4
- path: materials/templates/requirements-baseline.md
  size: 591
  sha256: E12B890FD798CD8C922A0459ED2A2D0D1AA04447BB3678D0EAFEC8B3B23B59CC
- path: materials/templates/risk-register.yaml
  size: 507
  sha256: 1F6913881D8EA7D8A13C8B89ED44D8E46C11DB28F11F697A243E55308173EF08
- path: materials/templates/role-capability-probe.yaml
  size: 836
  sha256: C8231DF817F1203695A85CA43DBAECE235A55DAE5EBA26F28029CCF8BD76074C
- path: materials/templates/role-contract.md
  size: 1043
  sha256: 4FC2E7E97C36A3FFD1D9AA6560B4ECADE071ED8378BFDAAF0E152E88230C54DC
- path: materials/templates/security-review.md
  size: 677
  sha256: 1BEF5FC9000BBE42941C7201384F3946E4776CAE938D953DEFCBDE2D79D9496D
- path: materials/templates/test-report.md
  size: 639
  sha256: B8C5CF653446B3404A2122879870FC2DC21999D64DBA7716E7FA00BB6A08764E
- path: materials/templates/test-strategy.md
  size: 676
  sha256: A765FEA64AF477C3EBCB88CE596332700258E0EDC55CEF0845BFA62D012A8F33
- path: materials/templates/threat-model.md
  size: 337
  sha256: 93B78653E029962452B08A7AD8AAF25E7020F0F8CDA043B5AFEF744CA83D8645
- path: materials/templates/work-packet.yaml
  size: 573
  sha256: 64D4F7C4956047B5679F2531F94DDFADFD9A1FB1D5C0E5072E6C091EAD19C063

当前结论：frozen / read-only review input / candidate-baseline-not-accepted
