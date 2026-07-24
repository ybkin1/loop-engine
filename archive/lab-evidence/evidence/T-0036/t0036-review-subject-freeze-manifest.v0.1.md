# T-0036 Review Subject Freeze Manifest v0.1

Captured before T-0036 registration writes on `2026-07-18`.

## Freeze Rule

The future formal review must recompute every row before substantive review. Any path, size, SHA-256, or `mtime_ns` mismatch returns `BLOCKED`. Registration-mutable T-0036 governance projections are not frozen candidate subjects and are checked through the registration changed-path manifest.

The 60 file subjects below include 23 canonical source-chain files plus all 37 subjects from the bound T-0035 final manifest. Registration-time comparison of the 37 final-manifest subjects found `0` mismatches.

| Class | Exact path | Size | SHA-256 | mtime_ns |
|---|---|---:|---|---:|
| source-chain | `.ai/evidence/T-0031/review-findings.v0.1.md` | 5528 | `F6341CB7D1E9B171F5A5A3E7EB5EC67407EB75E98392F5151DD3296A8C996F98` | 1783992961044242900 |
| source-chain | `.ai/evidence/T-0031/repair-planning.v0.1.md` | 6101 | `E7C2946835A099232CDF24F73F05E2D69C9E060AE931DBB58F0ECCF01D49DB95` | 1783992961050242100 |
| source-chain | `.ai/evidence/T-0033/isolated-candidate-activation-boundary-recovery.decision-packet.v0.1.md` | 6163 | `EBC5208B8AF4C6852CCE0AA5D78B58E2FD562EC3BBB1F6EA95BB15B195CE5BAB` | 1784010511319100200 |
| source-chain | `.ai/evidence/T-0033/changed-path-baseline.v0.1.md` | 1684 | `10F662C22E93570A4C5C2C19AC7309EEEC769979E37D074F758FEC6C44554E6E` | 1784010438610975800 |
| source-chain | `.ai/evidence/T-0033/commands.md` | 20547 | `BEE45B110926392A613A822DDA3921D5875A6859A437A0E5C77A2BD1C1819C43` | 1784094764687397300 |
| source-chain | `.ai/evidence/T-0034/t0034-requirements-baseline.v0.2.md` | 7914 | `41931EE234718792F6CE386EBBD1F300FBA386EAF8ACE7F62EC542054FB6F1B7` | 1784184051064036700 |
| source-chain | `.ai/evidence/T-0034/t0034-requirements-baseline.v0.3.md` | 3043 | `E99F7FA67FC56A2F4734E5E73F8D9A20B3CEC9AF330E8828E4BDD423FE0F4540` | 1784251851897068000 |
| source-chain | `.ai/evidence/T-0034/project-continuity-contract.v0.2.md` | 6593 | `EDCE58BBE0D74744AFB5803FD2CFDCBC361CA084F78DE9C83E77CAF961832766` | 1784182349542518100 |
| source-chain | `.ai/evidence/T-0034/handoff-writing-standard.v0.1.md` | 15070 | `5DF3B70ACA44B3593111F002AD3C132BA0374B447587E1E6D86A8BF3D64B416C` | 1784104555717386300 |
| source-chain | `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.2.md` | 7229 | `3F3D8C6905E476E35300DC189BA9A69F3722FBADDDC6659AA481716CA196508D` | 1784182546271880300 |
| source-chain | `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.3.md` | 3547 | `616BC96184332318FD0CF87BD1143D5BAC212BE74F2D35647D9D8910B5A2D2BE` | 1784251915758577900 |
| source-chain | `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.4.md` | 3212 | `3D60C80C48C503ED42BF2F6E75347C3EA6D96C27D6EB0F9C0E13B8E64E544C4F` | 1784264352532358300 |
| source-chain | `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-executor-report.v0.1.md` | 1534 | `7974216E3AF727F615D13CEC8EB95EC6959F2DF3B8A3A60F618DE257D25A931C` | 1784264606471548000 |
| source-chain | `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview.v0.1.md` | 4567 | `745EB5A419498011377627B6BB1927A170E7F1ABB416E2D862A2F79FE5EA1BC8` | 1784267911091281300 |
| source-chain | `.ai/evidence/T-0034/downstream-program-plan.v0.1.md` | 4282 | `1949EED355B3F87C8322B150811EABD959FE0837A35C1E6FA1CCB1FF89C71146` | 1784097041696250600 |
| source-chain | `.ai/tasks/T-0035.md` | 4119 | `AAA659BF41079A2D847C9693CBF341B0033305ACBA3B56C52BCF163BD85F1F39` | 1784365859723938600 |
| source-chain | `.ai/evidence/T-0035/t0035-implementation-decision-packet.v0.1.md` | 12953 | `B9D5FC8E00E0A27480C61F59E58972202D2BA888C39567A7AF9B7D975E105B71` | 1784361088471231000 |
| source-chain | `.ai/evidence/T-0035/t0035-implementation-preflight.v0.1.md` | 2591 | `AD4E071C1713C36F51303ADCC77E82CDF2E0231602CAA97CCC40264F9DE8CB83` | 1784361973263881800 |
| source-chain | `.ai/evidence/T-0035/t0035-implementation-commands.v0.1.md` | 2882 | `20994E780ACC5CCD65F7F6A4701FED1ACC4DABC22BED6296296709AC33E75BCF` | 1784365166417284000 |
| source-chain | `.ai/evidence/T-0035/t0035-implementation-executor-report.v0.1.md` | 3105 | `88A5B5EABB5F9B80E272916BA160640D585961CC081DF917A46E1B94FA1F9425` | 1784365859720938600 |
| source-chain | `.ai/evidence/T-0035/t0035-final-validation-manifest.v0.1.yaml` | 8783 | `1DC5615694AFE5B9638B16D11E14B23D813F156B1314013A3A8202C73549DE7F` | 1784365202584919200 |
| source-chain | `.ai/evidence/T-0035/t0035-protected-boundary-postcheck.v0.1.md` | 1268 | `8F980ECA6E97400CFB735FADEC385141D8102327B53E8203577C54A9336E8A8E` | 1784365859721939500 |
| source-chain | `.ai/evidence/T-0035/t0035-implementation-changed-path-manifest.v0.1.md` | 1997 | `C45EF41422539C2FDD0943DF0EF2B43F282924F0659F1223D878C9D3E268DF53` | 1784365859722939900 |
| manifest-subject | `candidates/T-0030-project-governor-repair/scripts/governor_lib.py` | 57743 | `94B4FA1E6BED24A4E5083D1FD4008199897EE177368893F04FAAE5FB00FBACEA` | 1784364687578125300 |
| manifest-subject | `candidates/T-0030-project-governor-repair/scripts/governance_action.py` | 4379 | `3FCAA031424656F7FAC29BACC61FEC2D4E036A20C5035F9066097D28BB683A1B` | 1784364489924666500 |
| manifest-subject | `candidates/T-0030-project-governor-repair/scripts/close_session.py` | 4671 | `F22CFB814C43073562B95B96AA385374569E7C2EE5E670711D0C1029AABA0EBD` | 1784363858891846700 |
| manifest-subject | `candidates/T-0030-project-governor-repair/scripts/validate_state.py` | 2004 | `BF533B91F5B32F1F21986271C8D0FDF678B2E31EBDE4B42F42F02144583B3525` | 1784362820568152600 |
| manifest-subject | `candidates/T-0030-project-governor-repair/scripts/audit_handoff.py` | 2900 | `30243CED5234ABBC62F2C56ED03B3FCDCE86BA7DE62AA6982831D29E8EDA0D6B` | 1784363858892847900 |
| manifest-subject | `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py` | 38049 | `BB6AE651979E5ADE29FA396A7C4922EE158EFE05E7B16E3C57B1CB5F9251219C` | 1784364711758771000 |
| manifest-subject | `candidates/T-0030-project-governor-repair/BOUNDARY.md` | 4439 | `7CB056EEDF1C9DDFEC6A8B1BCCF688B26270E4F6498AAF92F1F6835FBC931DAB` | 1784364053087173700 |
| manifest-subject | `candidates/T-0030-project-governor-repair/PROVENANCE.yaml` | 8338 | `51FC07BC36C044CE5DD443349ABD09708C0B8AF6848766E70582F049D97E0BB2` | 1784364838967991700 |
| manifest-subject | `AGENTS.md` | 4105 | `7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA` | 1783499811804132500 |
| manifest-subject | `candidates/T-0030-project-governor-repair/NOT_INSTALLED` | 187 | `CA19715176E4FD328515F5ECD36D1EB7B91AF7C70BC767C3F61EF9A52B2AB7E5` | 1784087348182704400 |
| manifest-subject | `candidates/T-0030-project-governor-repair/NOT_ACTIVATED` | 178 | `9BBB093D9C5E6129B1CE440575E9D289366FCDC7223C944532376D0C2E033EAE` | 1784087348183686900 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/agents/openai.yaml` | 250 | `53B626C9F106D170B283209B2F204EAC43C3703E394B2F9C7A4571A66E4BCCD5` | 1782818728569381000 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/audit_handoff.py` | 3529 | `92DFA111C209CEE7283B1451E947C4E94EB5067A34A8AC9EC97674A78CB12545` | 1783940059095554700 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/close_session.py` | 4828 | `28D562B5BB1B80F28589E25DCE355472F058D39C2F94680E309BAB36AEED19D4` | 1783939246089864600 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/governor_lib.py` | 19247 | `7D0344AF52F46DED67F4328A016D17D81A921F4903EA6F126A06D02DD11FACEA` | 1783939714226872500 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/init_project.py` | 875 | `BC3751AFF66B99E7DB3DE6B3869E1E441FB4F5165E9281001DFA8D20E80C2719` | 1782818816711273400 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/new_task.py` | 2157 | `F3D7D057622BF2D674632385690822EA0995EE176AFA1997B66691903C62142F` | 1782818816713275800 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/scripts/validate_state.py` | 1926 | `D8C9834DC77CC208785811647A61AB7A3D2B7FB6D2D866C7B5602C1FF23EC5D2` | 1783939276916804800 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/SKILL.md` | 3462 | `BF556AE4E5BAAD4A68D5A22ABDF2BC600F979FCA365AAED2F5BCB27096CDDA7D` | 1782818728541377500 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/ACCEPTANCE.md` | 139 | `88935D966C4CD3AB698C2BA5829FE0125BE14D37072784AAEE91A254510BE2C0` | 1782818728553378800 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/ARCHITECTURE.md` | 89 | `AB6AC42E0AD16EFD0272CF820B7BBDF98989D06677A8D219DA2F2305AD7B3DFC` | 1782818728545377800 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/CODEMAP.md` | 69 | `67378FA8632483726E53E02D4CE95ECCB8E536C1AEE4213EC7937EC8CC9EFD8C` | 1782818728549381100 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/CODING_STANDARDS.md` | 251 | `4C983B73E738A9861B80F5EBC0C6F96215DA49B0E339F1B0A15E7161655D9082` | 1782818728547379400 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/CONTRACTS.md` | 75 | `0767868E02A5B00B3F10C62C594070D6B4C755138CEB3DE415D6CE61579FF75A` | 1782818728546379900 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/CONVENTIONS.md` | 105 | `45F29637AA2ED0027FB1F1E733B64B23871183DB1694C357F44E4C046DD43403` | 1782818728548380000 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/DECISIONS.md` | 154 | `CA9875D2539DBAF8CDAA9A8769AB2F883369602DCEDC4C35F3820C9BE99A535B` | 1782818728554379000 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/gates.yaml` | 28 | `50C4E5523B23726757D58505134F413DD2DE2919488EF203AD423C3DA2E8B9C5` | 1782818728558378900 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/HANDOFF.md` | 478 | `991161A5B573B42C28F91E7E8C9FF3CB77EBFE4A9807D90A1FD3DEFABCB572F8` | 1782818728559377400 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/KNOWN_ISSUES.md` | 49 | `C5532D2B63F092E08278EF040797298D1CF05DBA042BE4DCCE3D4798D1A6D8DD` | 1782818728555379100 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/NON_GOALS.md` | 19 | `D8BF8C39BD6A2830F334BBAC19F1648E87AAD4A3A4B178DE98C67AA3D491E96E` | 1782818728544383100 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/PROGRESS.md` | 81 | `18EC730F61F4BA7B2510E1D90C645731412E4267A66C2124EC7E00E624D99A8A` | 1782818728551379900 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/PROJECT.md` | 186 | `B17ADA88155FFD09E88849EFD84AC62875267C264825B6BDBF212C388590C0A2` | 1782818728544383100 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/QUALITY_GATES.md` | 260 | `3CB94108AC4276EE2FE49296EC0EEE738C00C5FF7CDAC072D8CA10265C6AE588` | 1782818728552382200 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/reviews/TEMPLATE.md` | 104 | `B1EFC031A1318A0551A625E0262E741870418C27E0563CD41BE3C7C3CF1D6A6B` | 1782818728561379500 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/state.yaml` | 140 | `749B7613E0CB96840A402AE9DB0E6DE80969D38D00C3C8BC032369B7E16973F2` | 1782818728556381000 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/task_graph.yaml` | 38 | `EEC956217ECFED83A14245C07246DFD9E4E65975908E3A0F7A922B9B7C8BE361` | 1782818728557380500 |
| manifest-subject | `C:/Users/Administrator/.codex/skills/project-governor/templates/ai/tasks/TEMPLATE.md` | 233 | `8A644A56878CE7F14EB9C7F978AE11D84B7E2042EBCF208CF9FFC42FE0BC5050` | 1782818728560382900 |

## Logical T-0035 Gate Record

Because `.ai/gates.yaml` is an authorized registration-mutable projection, the T-0035 Gate node is frozen semantically rather than freezing the whole file.

- Source path: `.ai/gates.yaml`.
- Gate ID: `G-T-0035-IMPLEMENT-T0030-REPAIR-AND-APPROVED-CONTINUITY-INTERFACES-IN-ISOLATED-CANDIDATE`.
- Canonicalization: UTF-8 JSON, keys sorted recursively, `ensure_ascii=false`, separators `(',', ':')`.
- Field count: `63`.
- Canonical JSON byte count: `11102`.
- Canonical JSON SHA-256: `1341D1E79A1D0715BEF7E1820ABEC5CFBE75EF75697E302F6FD6902892B57F63`.

## Registration-time Boundary Snapshot

- Candidate inventory: 10 files, 2 directories, 0 cache/compiled artifacts, 0 reparse points.
- Candidate root entries in `PATH`: 0.
- Candidate root entries in `PYTHONPATH`: 0.
- `PATH` SHA-256: `D51DDF92E46FCAD4A286A5919F37A22B9D12C9C9C29F955D0B3D9D7E61121BE7`.
- `PYTHONPATH` SHA-256: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.

Formal review must independently recompute these values; this registration snapshot is not a review verdict.
