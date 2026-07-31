# T-0087 U1: Checkers/Guards 能力注册表化 — 设计证据（capability-registry）

> **T-0087 U1 交付物 | 2026-08-01 | developer 子代理 | 任务：G-T-0087-REQUIREMENTS（approved）**

## 1. 借鉴来源

StaffDeck（OpenBMB/StaffDeck）`capabilities/registry.py`（164 行）的 CapabilityRegistry
模式，经 T-0086 对标（`.ai/evidence/T-0086/staffdeck-benchmark.md` U1）确定落地：

| StaffDeck 机制 | loop-engine 落地 |
|---|---|
| 显式注册（capability 绑定） | `CapabilityBinding` + `CapabilityRegistry.register()` |
| `seal()` 冻结（seal 后 register 抛错） | 同语义：`RuntimeError`，快照只读 |
| 确定性快照 + sha256 snapshot_id | `snapshot(requested)` → 键排序 + canonical JSON → sha256 |
| 只读映射 | `CapabilitySnapshot.entries`（`MappingProxyType`） |
| fail-closed 重水合（版本不匹配抛错，不静默降级） | `rehydrate()`：版本/契约不匹配 → `ValueError`，未知能力 → `LookupError`，篡改 id → `ValueError` |

解决的问题：`guard_health.py`（T-0083）只测"guard 死亡"（正/负对照电池，fail-closed），
测不到两类治理资产失效——**遗漏**（实现文件存在但未登记，guard 活着却不在治理面内）与
**漂移**（已登记但实现文件被改，哈希/版本与登记时不一致）。注册表补齐这两类。

## 2. 结构

### 2.1 `loop_core/capability_registry.py`（新增）

- **`CapabilityBinding`**（frozen dataclass）：`capability_id` / `provider_id`
  （"checker"|"guard"）/ `implementation_path`（相对项目根，正斜杠）/
  `version` / `contract_version` / `description` / `health_required` /
  `implementation_hash`（实现文件 sha256，漂移检测基准）。`to_dict()`/`from_dict()`
  用于确定性序列化与重水合。
- **`CapabilityRegistry`**：
  - `register(binding)` — seal 前登记；重复 id 抛 `ValueError`；seal 后抛 `RuntimeError`（AC-01）
  - `seal()` — 冻结
  - `require(capability_id)` — 缺失抛 `LookupError`（不静默）
  - `snapshot(requested=None)` — 筛选 → 排序 → 确定性 JSON → sha256 snapshot_id；
    未知 requested id 抛 `LookupError`（不静默丢弃）
  - `rehydrate(payload)` — fail-closed（见 §3）
- **`CapabilitySnapshot`**（frozen dataclass）：`entries`（`MappingProxyType` 只读）/
  `canonical_json` / `snapshot_id`。snapshot_id 由 canonical_json 派生，不进 canonical（避免循环）。
- **`build_default_registry(project_root, seal=True)`**：登记 `.ai/checkers/` 3 个
  （compile_gate、run_governance_checks、validate_gate_register）+ `.ai/guards/` 1 个
  （policy_guard）。版本号从文件实际内容派生：`detect_version()` 读文件头
  `__version__ = "x.y.z"` 常量，无则用实现文件 sha256 前缀（12 hex）——
  内容变 → 版本变，漂移可见。契约版本：checkers → `checker-result.schema.yaml@1`，
  guards → `guard-decision.schema.yaml@1`（与 `.ai/schemas/` 输出契约对应）。

### 2.2 确定性序列化（AC-01）

- 条目按 `capability_id` 排序；`json.dumps(sort_keys=True, ensure_ascii=False,
  separators=(",", ":"))`；无时间戳/随机字段 → 同输入同输出同 sha256。
- 有测试证明：同一组绑定（不同实例、不同登记顺序）→ 相同 `canonical_json` 与 `snapshot_id`。

### 2.3 `loop_core/guard_health.py`（扩展，T-0087 U1 集成）

- 构造函数新增可选 `registry` 参数（默认 `build_default_registry(root)`），向后兼容。
- **`missing_detection()`**：扫描 `.ai/checkers/*.py`、`.ai/guards/*.py`（跳过
  `__init__.py`）与注册表 `implementation_path` 比对，未登记 → `MISSING` finding。
- **`drift_detection()`**：对每个已登记绑定，重算实现文件 sha256 与登记的
  `implementation_hash` 比对（文件缺失也算漂移）→ `DRIFT` finding。
- **`integrity_check()`**：三类合一 — `death`（原电池，语义不变）+ `missing` + `drift`；
  `overall` 只由 death 驱动。MISSING/DRIFT 为 `severity: "report"`，**不阻断主流程**；
  死亡检测（BROKEN/DORMANT → FAIL）**不放松**（AC-02）。
- 既有 `summary()`/`run()`/电池逻辑未改动（仅 import + 构造签名扩展 + 新增方法）。

### 2.4 `tools/tool_registry_status.py`（新增 CLI）

列出注册表快照（snapshot_id + 绑定明细）+ 三类完整性检测；`--report` 写证据
`.ai/evidence/T-0087/capability-registry/status.json`。退出码：0=全健康，
1=仅 report 级 finding（MISSING/DRIFT，不阻断），2=guard 死亡（fail-closed，同既有语义）。

## 3. fail-closed 语义（AC-03）

`rehydrate(payload)` 逐条校验，任何不匹配显式抛错，绝不静默降级：

1. payload 携带 snapshot_id 且与按 entries 重算的 id 不一致 → `ValueError`（篡改/损坏）；
2. payload 条目能力 id 不在（sealed）注册表中 → `LookupError`；
3. 条目 `version` 与注册表不一致 → `ValueError`；
4. 条目 `contract_version` 与注册表不一致 → `ValueError`。

配套测试模拟真实场景：旧注册表签发的快照（快照内部自洽、id 有效）与当前注册表
版本/契约不一致 → 抛错，而不是把旧绑定悄悄接受。

## 4. 与 guard_health 的集成方式（AC-02）

```
GuardHealth.integrity_check()
├── death   : run() 正/负对照电池 → ALIVE/DORMANT/BROKEN（已有，fail-closed）
├── missing : 磁盘 *.py 存在但未登记          → MISSING（report）
└── drift   : 已登记但文件哈希/版本不一致      → DRIFT（report）
overall = death.overall   # missing/drift 永不改写 overall
```

三类检测各有测试；并有两项边界测试：missing/drift 存在但 guard 全 ALIVE → overall 仍
PASS（report 级不阻断）；guard DORMANT 且 missing 存在 → overall 仍 FAIL（死亡不放松）。

## 5. 验收映射

| AC | 证据 |
|---|---|
| AC-01（seal 不可变 + 快照确定性指纹） | `test_seal_prevents_register_after_seal`、`test_snapshot_deterministic_same_input_same_fingerprint`、`test_snapshot_id_is_sha256_of_canonical_json` |
| AC-02（三类检测均有测试 + report 级不阻断） | `test_missing_detection_*`、`test_drift_detection_*`、`test_missing_drift_are_report_level_and_never_flip_overall`、`test_death_detection_stays_fail_closed`、`test_live_repo_has_no_missing_or_drift` |
| AC-03（重水合 fail-closed） | `test_rehydrate_version_mismatch_raises_value_error`、`test_rehydrate_contract_mismatch_raises_value_error`、`test_rehydrate_unknown_capability_raises_lookup_error`、`test_rehydrate_tampered_snapshot_id_raises_value_error`、`test_rehydrate_roundtrip_ok` |

## 6. 变更文件

| 文件 | 变更 |
|---|---|
| `loop_core/capability_registry.py` | 新增（~300 行）：Binding/Registry/Snapshot/rehydrate/build_default_registry |
| `loop_core/guard_health.py` | 扩展：registry 注入 + missing/drift/integrity_check（death 语义不变） |
| `tools/tool_registry_status.py` | 新增：注册表状态 CLI |
| `tests/test_capability_registry.py` | 新增：21 个测试（AC-01/02/03） |
| `.ai/evidence/T-0087/capability-registry/status.json` | 实测证据（快照 id：见文件） |
| `.ai/evidence/T-0087/capability-registry/design.md` | 本文档 |
