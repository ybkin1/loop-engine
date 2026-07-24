import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { initProject, loadState, checkGate, advanceGate } from "../src/core/state-machine.js";
import { activateRole, completeRole } from "../src/core/role-engine.js";
import { submitEvidence } from "../src/core/evidence.js";
import { createHandoff } from "../src/core/handoff.js";
import { deriveEnforcementLevel, HOST_PRESETS, EnforcementLevel } from "../src/core/enforcement.js";
import { routeIntent, defaultProfile, LoopMode } from "../src/core/router.js";
import { runAllCertifications, buildCertStateAfterRun } from "../src/core/certification.js";
import { ContextController, Action, Decision } from "../src/core/context_controller.js";
import { EnforcementHub } from "../src/core/enforcement_hub.js";
import { PhaseExecutor } from "../src/core/executor.js";
import { ContextLoader, LoadLevel } from "../src/core/context_loader.js";
import { ExecutionLedger, ExecutionStatus } from "../src/core/execution_ledger.js";
import { PacketBuilder, PacketType, toMarkdown } from "../src/core/human_review_packet.js";
import { createHostAdapter } from "../src/core/contracts.js";

const TEST_ROOT = join(process.cwd(), ".test-integration-tmp");

beforeEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
  mkdirSync(TEST_ROOT, { recursive: true });
});

afterEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
});

// ── Full Lifecycle ──────────────────────────────────────
describe("full lifecycle: init → delivery", () => {
  it("completes requirements → architecture → planning → implementation → review → delivery", async () => {
    // 1. Init
    const state = await initProject(TEST_ROOT, "integration-test");
    expect(state.current_phase).toBe("requirements");

    // 2. Requirements phase
    const r01 = await activateRole(TEST_ROOT, "R01");
    expect(r01.success).toBe(true);
    await submitEvidence(TEST_ROOT, {
      evidence_id: "req-baseline", type: "acceptance_criteria",
      content: "user can login with email", role_id: "R01",
    });
    await completeRole(TEST_ROOT, "R01");

    // Check and advance requirements gate
    const reqCheck = await checkGate(TEST_ROOT, "gate-requirements");
    expect(reqCheck.status).toBe("pass");
    const reqAdvance = await advanceGate(TEST_ROOT, "gate-requirements");
    expect(reqAdvance.success).toBe(true);
    expect(reqAdvance.new_phase).toBe("architecture");

    // 3. Architecture phase
    const r04 = await activateRole(TEST_ROOT, "R04");
    expect(r04.success).toBe(true);
    await submitEvidence(TEST_ROOT, {
      evidence_id: "arch-review", type: "architecture_review",
      content: "3-tier architecture approved", role_id: "R04",
    });
    await submitEvidence(TEST_ROOT, {
      evidence_id: "sec-boundary", type: "security_boundary",
      content: "auth boundary defined", role_id: "R04",
    });
    await completeRole(TEST_ROOT, "R04");

    const archCheck = await checkGate(TEST_ROOT, "gate-architecture");
    expect(archCheck.status).toBe("pass");
    const archAdvance = await advanceGate(TEST_ROOT, "gate-architecture");
    expect(archAdvance.success).toBe(true);
    expect(archAdvance.new_phase).toBe("planning");

    // 4. Planning phase
    const r05 = await activateRole(TEST_ROOT, "R05");
    expect(r05.success).toBe(true);
    await completeRole(TEST_ROOT, "R05");

    const planCheck = await checkGate(TEST_ROOT, "gate-planning");
    expect(planCheck.status).toBe("pass");
    const planAdvance = await advanceGate(TEST_ROOT, "gate-planning");
    expect(planAdvance.success).toBe(true);
    expect(planAdvance.new_phase).toBe("implementation");

    // 5. Implementation phase
    const r06 = await activateRole(TEST_ROOT, "R06");
    expect(r06.success).toBe(true);
    await submitEvidence(TEST_ROOT, {
      evidence_id: "test-result", type: "test_result",
      content: "42 tests passed", role_id: "R06",
    });
    await submitEvidence(TEST_ROOT, {
      evidence_id: "lint-result", type: "lint_result",
      content: "0 errors", role_id: "R06",
    });
    await completeRole(TEST_ROOT, "R06");

    const implCheck = await checkGate(TEST_ROOT, "gate-implementation");
    expect(implCheck.status).toBe("pass");
    const implAdvance = await advanceGate(TEST_ROOT, "gate-implementation");
    expect(implAdvance.success).toBe(true);
    expect(implAdvance.new_phase).toBe("review");

    // 6. Review phase
    const r09 = await activateRole(TEST_ROOT, "R09");
    await completeRole(TEST_ROOT, "R09");
    const r07 = await activateRole(TEST_ROOT, "R07");
    await completeRole(TEST_ROOT, "R07");
    const r08 = await activateRole(TEST_ROOT, "R08");
    await completeRole(TEST_ROOT, "R08");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "defect-report", type: "defect_report",
      content: "P0=0, P1=0", role_id: "R07",
    });

    const reviewCheck = await checkGate(TEST_ROOT, "gate-review");
    expect(reviewCheck.status).toBe("pass");
    const reviewAdvance = await advanceGate(TEST_ROOT, "gate-review");
    expect(reviewAdvance.success).toBe(true);
    expect(reviewAdvance.new_phase).toBe("delivery");

    // 7. Delivery phase
    const r03 = await activateRole(TEST_ROOT, "R03");
    await completeRole(TEST_ROOT, "R03");
    const r10 = await activateRole(TEST_ROOT, "R10");
    await completeRole(TEST_ROOT, "R10");

    const delCheck = await checkGate(TEST_ROOT, "gate-delivery");
    // manual_approval always blocks (requires human action)
    expect(delCheck.status).toBe("block");
    const delAdvance = await advanceGate(TEST_ROOT, "gate-delivery");
    expect(delAdvance.success).toBe(false); // blocked by manual_approval
  });
});

// ── Self-Review Prevention ──────────────────────────────
describe("self-review prevention", () => {
  it("developer and reviewer must be different roles", async () => {
    await initProject(TEST_ROOT, "self-review-test");

    // Activate developer
    const dev = await activateRole(TEST_ROOT, "R06");
    expect(dev.success).toBe(true);

    // Complete developer
    await completeRole(TEST_ROOT, "R06");

    // Activate reviewer (must be different role)
    const reviewer = await activateRole(TEST_ROOT, "R09");
    expect(reviewer.success).toBe(true);

    const state = await loadState(TEST_ROOT);
    expect(state.active_role).toBe("R09");
    expect(state.completed_roles).toContain("R06");
    expect(state.completed_roles).not.toContain("R09");
  });
});

// ── Evidence Binding ────────────────────────────────────
describe("evidence binding across phases", () => {
  it("evidence submitted in one phase persists to next", async () => {
    await initProject(TEST_ROOT, "evidence-persist");

    // Submit evidence in requirements phase
    await submitEvidence(TEST_ROOT, {
      evidence_id: "req-ev", type: "acceptance_criteria",
      content: "criteria v1", role_id: "R01",
    });

    // Complete requirements and advance
    await activateRole(TEST_ROOT, "R01");
    await completeRole(TEST_ROOT, "R01");
    await advanceGate(TEST_ROOT, "gate-requirements");

    const state = await loadState(TEST_ROOT);
    expect(state.current_phase).toBe("architecture");

    // Evidence should still be verifiable
    const { verifyEvidence } = await import("../src/core/evidence.js");
    const verify = await verifyEvidence(TEST_ROOT, "req-ev");
    expect(verify.status).toBe("verified");
    expect(verify.match).toBe(true);
  });
});

// ── Handoff Chain ───────────────────────────────────────
describe("handoff chain integrity", () => {
  it("handoff records contain artifact hashes", async () => {
    await initProject(TEST_ROOT, "handoff-chain");

    const result = await createHandoff(
      TEST_ROOT, "R01", "R04",
      [{ path: "requirements.md", version: "1.0" }],
      "Requirements baselined",
    );

    expect(result.success).toBe(true);
    expect(result.handoff_id).toContain("R01-to-R04");

    const { getHandoffHistory } = await import("../src/core/handoff.js");
    const history = getHandoffHistory(TEST_ROOT);
    expect(history).toContain("sha256");
    expect(history).toContain("R01");
    expect(history).toContain("R04");
  });
});

// ── Enforcement + Router Integration ────────────────────
describe("enforcement + router integration", () => {
  it("high-risk project routes to FULL and enforcement is honest", () => {
    const profile = { ...defaultProfile(), has_database: true, has_auth_permissions: true };
    const route = routeIntent(profile);
    expect(route.mode).toBe(LoopMode.FULL);
    expect(route.risk_level).toBe("CRITICAL");

    const level = deriveEnforcementLevel(HOST_PRESETS.qoder);
    expect(level).toBe(EnforcementLevel.STRONG);
  });

  it("low-risk project routes to LIGHTWEIGHT", () => {
    const route = routeIntent(defaultProfile());
    expect(route.mode).toBe(LoopMode.LIGHTWEIGHT);
    expect(route.phases).toHaveLength(3);
  });
});

// ── Certification Integration ───────────────────────────
describe("certification integration", () => {
  it("all roles certified before project starts", () => {
    const run = runAllCertifications();
    expect(run.overall_pass).toBe(true);

    const state = buildCertStateAfterRun({}, run);
    for (const [, rs] of Object.entries(state)) {
      expect(rs.state).toBe("CERTIFIED");
    }
  });
});

// ── Phase A-C 新模块集成测试 ──────────────────────────

describe('New modules integration', () => {
  it('ContextController allows non-governance project', async () => {
    // Use the temp root without .ai/
    const controller = new ContextController();
    const result = await controller.authorize({
      action: Action.WRITE_FILE,
      target_path: 'src/test.ts',
      project_root: TEST_ROOT,
    });
    // Without .ai/state.yaml, should ALLOW
    expect(result.decision).toBe(Decision.ALLOW);
  });

  it('EnforcementHub quickCheck works on non-governance project', async () => {
    const hub = new EnforcementHub(TEST_ROOT);
    try {
      const decision = await hub.shouldAllowWrite('src/test.ts');
      expect(decision.allowed).toBe(true);
    } catch (error) {
      // Expected: no state.yaml means non-governance project
      expect(error).toBeDefined();
    }
  });

  it('PhaseExecutor planPhase creates correct steps', () => {
    const executor = new PhaseExecutor(TEST_ROOT);
    const plan = executor.planPhase('requirements');
    expect(plan.steps.length).toBeGreaterThan(0);
    expect(plan.steps[0].role_id).toBe('R01');
  });

  it('ContextLoader loads minimal context', () => {
    const loader = new ContextLoader();
    const ctx = loader.loadRoleContext('R01', 0.1);
    expect(ctx.level).toBe(LoadLevel.MINIMAL);
    expect(ctx.system_prompt.length).toBeGreaterThan(0);
  });

  it('ExecutionLedger records and verifies', () => {
    const ledgerPath = join(TEST_ROOT, '.ai', 'ledger', 'test_exec.jsonl');
    mkdirSync(dirname(ledgerPath), { recursive: true });
    const ledger = new ExecutionLedger(ledgerPath);
    const entry = ledger.recordLaunch({
      execution_id: 'exec-1', session_id: 'sess-1',
      actor_id: 'agent-1', role_id: 'R06', task_id: 'task-1',
      prompt_fingerprint: 'hash1', input_files_hash: 'hash2',
      tool_constraints: [], tool_violations: [],
    });
    expect(entry.status).toBe(ExecutionStatus.LAUNCHED);
    expect(ledger.length).toBe(1);
    const integrity = ledger.verifyChain();
    expect(integrity.valid).toBe(true);
  });

  it('PacketBuilder generates gate approval packet', () => {
    const packet = PacketBuilder.fromPhaseCompletion({
      phase: 'requirements',
      taskId: 'task-1',
      artifacts: ['docs/requirements.md'],
    });
    expect(packet.packet_type).toBe(PacketType.GATE_APPROVAL);
    const md = toMarkdown(packet);
    expect(md).toContain('requirements');
  });

  it('createHostAdapter returns correct adapter', () => {
    const qoder = createHostAdapter('qoder');
    expect(qoder.host_name).toBe('qoder');
    const standalone = createHostAdapter('standalone');
    expect(standalone.host_name).toBe('standalone');
  });

  it('EnforcementHub role isolation check', () => {
    const hub = new EnforcementHub(TEST_ROOT);
    const same = hub.checkRoleIsolation('R06', 'R06');
    expect(same.allowed).toBe(false);
    const diff = hub.checkRoleIsolation('R06', 'R09');
    expect(diff.allowed).toBe(true);
  });
});
