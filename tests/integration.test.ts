import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { initProject, loadState, checkGate, advanceGate } from "../src/core/state-machine.js";
import { activateRole, completeRole } from "../src/core/role-engine.js";
import { submitEvidence } from "../src/core/evidence.js";
import { createHandoff } from "../src/core/handoff.js";
import { deriveEnforcementLevel, HOST_PRESETS, EnforcementLevel } from "../src/core/enforcement.js";
import { routeIntent, defaultProfile, LoopMode } from "../src/core/router.js";
import { runAllCertifications, buildCertStateAfterRun } from "../src/core/certification.js";

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
