import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, rmSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  initProject,
  initProjectExtended,
  loadState,
  saveState,
  checkGate,
  advanceGate,
  approveGate,
  isUserApproved,
  evalEvidenceCondition,
} from "../src/core/state-machine.js";
import { activateRole, completeRole } from "../src/core/role-engine.js";

const TEST_ROOT = join(process.cwd(), ".test-approval-tmp");

beforeEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
  mkdirSync(TEST_ROOT, { recursive: true });
});

afterEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
});

/** 构造 6-phase 项目并推进到 delivery 阶段（作为 manual_approval 测试基底） */
async function setupDeliveryPhase() {
  await initProject(TEST_ROOT, "approve-test");
  const state = await loadState(TEST_ROOT);
  state.current_phase = "delivery";
  state.current_gate_id = "gate-delivery";
  await saveState(TEST_ROOT, state);
}

describe("approveGate", () => {
  it("rejects unknown gate", async () => {
    await setupDeliveryPhase();
    const result = await approveGate(TEST_ROOT, "nonexistent");
    expect(result.success).toBe(false);
    expect(result.error).toContain("Gate not found");
  });

  it("rejects gate without manual_approval condition", async () => {
    await setupDeliveryPhase();
    const result = await approveGate(TEST_ROOT, "gate-requirements");
    expect(result.success).toBe(false);
    expect(result.error).toContain("no manual_approval condition");
  });

  it("records approval, persists to state, and appends audit ledger", async () => {
    await setupDeliveryPhase();
    const result = await approveGate(TEST_ROOT, "gate-delivery", "user accepted release");
    expect(result.success).toBe(true);
    expect(result.approved_at).toBeTruthy();

    const state = await loadState(TEST_ROOT);
    const rec = state.user_approvals?.["gate-delivery"];
    expect(rec).toBeDefined();
    expect(rec!.approved_by).toBe("user");
    expect(rec!.note).toBe("user accepted release");
    expect(isUserApproved(state, "gate-delivery")).toBe(true);

    // 审计账本必须包含批准事件（P0-3 可追溯性）
    const ledger = readFileSync(join(TEST_ROOT, ".ai", "audit_ledger.jsonl"), "utf-8");
    expect(ledger).toContain("user_gate_approval");
  });

  it("rejects forged approval records (missing gate_id / wrong approved_by)", async () => {
    await setupDeliveryPhase();
    const state = await loadState(TEST_ROOT);
    // 伪造：approved_by 非 user
    state.user_approvals = { "gate-delivery": { gate_id: "gate-delivery", approved_by: "R11", approved_at: new Date().toISOString() } };
    await saveState(TEST_ROOT, state);
    expect(isUserApproved(await loadState(TEST_ROOT), "gate-delivery")).toBe(false);

    // 伪造：gate_id 不匹配
    state.user_approvals = { "gate-delivery": { gate_id: "gate-other", approved_by: "user", approved_at: new Date().toISOString() } };
    await saveState(TEST_ROOT, state);
    expect(isUserApproved(await loadState(TEST_ROOT), "gate-delivery")).toBe(false);
  });
});

describe("manual_approval gate condition", () => {
  it("checkGate reports manual_approval missing when user has not approved", async () => {
    await setupDeliveryPhase();
    const result = await checkGate(TEST_ROOT, "gate-delivery");
    expect(result.status).toBe("block");
    const manual = result.missing_conditions.find(m => m.type === "manual_approval");
    expect(manual).toBeDefined();
    expect(manual!.description).toContain("用户验收");
  });

  it("advanceGate succeeds only when role conditions met AND user approved AND gate is current", async () => {
    await setupDeliveryPhase();

    for (const role of ["R03", "R10"]) {
      await activateRole(TEST_ROOT, role);
      await completeRole(TEST_ROOT, role);
    }

    // 未批准 → 仍 blocked
    const blocked = await advanceGate(TEST_ROOT, "gate-delivery");
    expect(blocked.success).toBe(false);
    expect(blocked.error).toContain("用户验收");

    // 用户批准 → 推进成功（delivery 是最后阶段，current_phase 保持 delivery）
    const approved = await approveGate(TEST_ROOT, "gate-delivery");
    expect(approved.success).toBe(true);
    const advanced = await advanceGate(TEST_ROOT, "gate-delivery");
    expect(advanced.success).toBe(true);
    expect(advanced.new_phase).toBe("delivery");
  });

  it("role verdict alone never satisfies manual_approval", async () => {
    await setupDeliveryPhase();
    const before = await checkGate(TEST_ROOT, "gate-delivery");
    expect(before.status).toBe("block");
    expect(before.missing_conditions.some(m => m.type === "manual_approval")).toBe(true);
  });
});

describe("P0-1/P0-2 regression: gate advance integrity", () => {
  it("rejects advancing a gate that is not the current gate (P0-2)", async () => {
    await initProject(TEST_ROOT, "integrity-test");
    // 当前 gate 是 gate-requirements，尝试推进 gate-delivery → 拒绝
    const result = await advanceGate(TEST_ROOT, "gate-delivery");
    expect(result.success).toBe(false);
    expect(result.error).toContain("not the current gate");
  });

  it("advancing the current gate is idempotent after pass (P0-1)", async () => {
    await initProject(TEST_ROOT, "integrity-test");
    // 满足 gate-requirements: R01 completed + acceptance_criteria evidence
    await activateRole(TEST_ROOT, "R01");
    await completeRole(TEST_ROOT, "R01");

    const { submitEvidence } = await import("../src/core/evidence.js");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "ev-accept",
      type: "acceptance_criteria",
      content: "acceptance defined",
      role_id: "R01",
    });

    const first = await advanceGate(TEST_ROOT, "gate-requirements");
    expect(first.success).toBe(true);
    expect(first.new_phase).toBe("architecture");

    const second = await advanceGate(TEST_ROOT, "gate-requirements");
    expect(second.success).toBe(true);
    expect(second.idempotent).toBe(true);
    // 幂等：阶段不得再次推进
    const state = await loadState(TEST_ROOT);
    expect(state.current_phase).toBe("architecture");
  });
});

describe("P1-1 regression: evidence condition evaluation", () => {
  it("evaluates numeric conditions fail-safe", () => {
    expect(evalEvidenceCondition("p0_count == 0", { metadata: { p0_count: 0 } })).toBe(true);
    expect(evalEvidenceCondition("p0_count == 0", { metadata: { p0_count: 2 } })).toBe(false);
    expect(evalEvidenceCondition("coverage >= 80", { metadata: { coverage: 85 } })).toBe(true);
    expect(evalEvidenceCondition("coverage >= 80", { metadata: { coverage: 70 } })).toBe(false);
    expect(evalEvidenceCondition("p0_count == 0", {})).toBe(false); // 缺字段 → 不满足
    expect(evalEvidenceCondition("!!!invalid", {})).toBe(false); // 无法解析 → fail-safe
  });

  it("evaluates string equality", () => {
    expect(evalEvidenceCondition('status == "passed"', { metadata: { status: "passed" } })).toBe(true);
    expect(evalEvidenceCondition('status == "passed"', { status: "failed" })).toBe(false);
  });
});

describe("extended 12-phase gates with approval", () => {
  it("gate-S6-delivery requires user approval and then passes check", async () => {
    await initProjectExtended(TEST_ROOT, "approve-ext", "FULL");
    await activateRole(TEST_ROOT, "R03");
    await completeRole(TEST_ROOT, "R03");

    const blocked = await checkGate(TEST_ROOT, "gate-S6-delivery");
    expect(blocked.status).toBe("block");

    await approveGate(TEST_ROOT, "gate-S6-delivery", "release approved");
    const passed = await checkGate(TEST_ROOT, "gate-S6-delivery");
    expect(passed.status).toBe("pass");
  }, 20000);

  it("S1 gate is unaffected by approval semantics (no manual_approval)", async () => {
    await initProjectExtended(TEST_ROOT, "approve-ext", "FULL");
    const result = await approveGate(TEST_ROOT, "gate-S1-requirements");
    expect(result.success).toBe(false);
    expect(result.error).toContain("no manual_approval condition");
  });
});
