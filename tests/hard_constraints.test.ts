import { describe, it, expect } from "vitest";
import { HardConstraints, ConstraintID, Severity, createEvidenceEnvelope } from "../src/core/hard_constraints.js";
import type { ConstraintContext } from "../src/core/hard_constraints.js";

const hc = new HardConstraints();

// ── C1: Requirements Baseline ──────────────────────────
describe("C1: Requirements Baseline", () => {
  it("pass — target_phase=S4 and S1-requirements=APPROVED", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S1-requirements": "APPROVED" },
    };
    const violations = hc.checkC1(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — target_phase=S4 and S1-requirements=PENDING", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S1-requirements": "PENDING" },
    };
    const violations = hc.checkC1(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
    expect(violations[0].constraint_id).toBe(ConstraintID.C1);
  });

  it("blocker — target_phase=S4 and no phase_gates", () => {
    const ctx: ConstraintContext = { target_phase: "S4" };
    const violations = hc.checkC1(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("skip — target_phase=S1 (C1 does not check itself)", () => {
    const ctx: ConstraintContext = { target_phase: "S1" };
    const violations = hc.checkC1(ctx);
    expect(violations).toHaveLength(0);
  });
});

// ── C2: Architecture Baseline ──────────────────────────
describe("C2: Architecture Baseline", () => {
  it("pass — target_phase=S4 and S2-architecture=APPROVED", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S2-architecture": "APPROVED" },
    };
    const violations = hc.checkC2(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — target_phase=S4 and S2-architecture=BLOCKED", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S2-architecture": "BLOCKED" },
    };
    const violations = hc.checkC2(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── C3: Task Package ───────────────────────────────────
describe("C3: Task Package", () => {
  it("pass — tasks have active task", () => {
    const ctx: ConstraintContext = {
      tasks: [{ id: "T1", status: "active" }, { id: "T2", status: "completed" }],
    };
    const violations = hc.checkC3(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — tasks is empty", () => {
    const ctx: ConstraintContext = { tasks: [] };
    const violations = hc.checkC3(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — all tasks completed (no active)", () => {
    const ctx: ConstraintContext = {
      tasks: [{ id: "T1", status: "completed" }, { id: "T2", status: "completed" }],
    };
    const violations = hc.checkC3(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── C4: Path Scope ─────────────────────────────────────
describe("C4: Path Scope", () => {
  it("pass — target_path in allowed_paths", () => {
    const ctx: ConstraintContext = {
      target_path: "src/index.ts",
      allowed_paths: ["src/", "tests/"],
    };
    const violations = hc.checkC4(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — target_path outside allowed_paths", () => {
    const ctx: ConstraintContext = {
      target_path: "config/secrets.json",
      allowed_paths: ["src/", "tests/"],
    };
    const violations = hc.checkC4(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — allowed_paths is empty", () => {
    const ctx: ConstraintContext = {
      target_path: "src/index.ts",
      allowed_paths: [],
    };
    const violations = hc.checkC4(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── C5: Verification Passed ────────────────────────────
describe("C5: Verification Passed", () => {
  it("pass — test/lint/build all PASS at S6", () => {
    const ctx: ConstraintContext = {
      target_phase: "S6",
      quality_results: { test: "PASS", lint: "PASS", build: "PASS" },
    };
    const violations = hc.checkC5(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — test=FAIL at S6", () => {
    const ctx: ConstraintContext = {
      target_phase: "S6",
      quality_results: { test: "FAIL", lint: "PASS", build: "PASS" },
    };
    const violations = hc.checkC5(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — missing lint result at S6", () => {
    const ctx: ConstraintContext = {
      target_phase: "S6",
      quality_results: { test: "PASS", build: "PASS" },
    };
    const violations = hc.checkC5(ctx);
    expect(violations.length).toBeGreaterThan(0);
  });
});

// ── C6: Independent Review ─────────────────────────────
describe("C6: Independent Review", () => {
  it("pass — independent-reviewer=PASS at S4", () => {
    const ctx: ConstraintContext = {
      current_phase: "S4",
      review_status: { "independent-reviewer": "PASS" },
    };
    const violations = hc.checkC6(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — independent-reviewer=FAIL at S4", () => {
    const ctx: ConstraintContext = {
      current_phase: "S4",
      review_status: { "independent-reviewer": "FAIL" },
    };
    const violations = hc.checkC6(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — no review status at S4", () => {
    const ctx: ConstraintContext = { current_phase: "S4" };
    const violations = hc.checkC6(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── C7: No Blockers ────────────────────────────────────
describe("C7: No Blockers", () => {
  it("pass — no blocked gates/tasks", () => {
    const ctx: ConstraintContext = {
      gates: [{ id: "g1", status: "PASSED" }],
      tasks: [{ id: "T1", status: "active" }],
    };
    const violations = hc.checkC7(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — has blocked gate", () => {
    const ctx: ConstraintContext = {
      gates: [{ id: "g1", status: "BLOCKED" }],
    };
    const violations = hc.checkC7(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — has blocked task", () => {
    const ctx: ConstraintContext = {
      tasks: [{ id: "T1", status: "BLOCKED" }],
    };
    const violations = hc.checkC7(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── C8: Evidence Freshness ─────────────────────────────
describe("C8: Evidence Freshness", () => {
  it("pass — all evidence is_fresh() and hash unchanged", () => {
    const future = new Date(Date.now() + 86400000).toISOString();
    const ctx: ConstraintContext = {
      evidence_list: [
        createEvidenceEnvelope("ev1", "abc123", "S1", future, new Date().toISOString()),
        createEvidenceEnvelope("ev2", "def456", "S2", future, new Date().toISOString()),
      ],
      current_hashes: { ev1: "abc123", ev2: "def456" },
    };
    const violations = hc.checkC8(ctx);
    expect(violations).toHaveLength(0);
  });

  it("blocker — has expired evidence", () => {
    const past = new Date(Date.now() - 86400000).toISOString();
    const ctx: ConstraintContext = {
      evidence_list: [
        createEvidenceEnvelope("ev1", "abc123", "S1", past, new Date().toISOString()),
      ],
    };
    const violations = hc.checkC8(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });

  it("blocker — has hash-changed evidence", () => {
    const future = new Date(Date.now() + 86400000).toISOString();
    const ctx: ConstraintContext = {
      evidence_list: [
        createEvidenceEnvelope("ev1", "abc123", "S1", future, new Date().toISOString()),
      ],
      current_hashes: { ev1: "DIFFERENT_HASH" },
    };
    const violations = hc.checkC8(ctx);
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].severity).toBe(Severity.BLOCKER);
  });
});

// ── checkAll Integration ───────────────────────────────
describe("checkAll integration", () => {
  it("all constraints pass → passed=true", () => {
    const future = new Date(Date.now() + 86400000).toISOString();
    const ctx: ConstraintContext = {
      target_phase: "S4",
      current_phase: "S4",
      phase_gates: { "S1-requirements": "APPROVED", "S2-architecture": "APPROVED" },
      tasks: [{ id: "T1", status: "active", allowed_paths: ["src/"] }],
      target_path: "src/index.ts",
      allowed_paths: ["src/"],
      quality_results: { test: "PASS", lint: "PASS", build: "PASS" },
      review_status: { "independent-reviewer": "PASS" },
      gates: [{ id: "g1", status: "PASSED" }],
      evidence_list: [
        createEvidenceEnvelope("ev1", "abc", "S1", future, new Date().toISOString()),
      ],
      current_hashes: { ev1: "abc" },
    };
    const result = hc.checkAll(ctx);
    expect(result.passed).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it("one BLOCKER → passed=false", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S1-requirements": "PENDING" },
      tasks: [{ id: "T1", status: "active" }],
    };
    const result = hc.checkAll(ctx);
    expect(result.passed).toBe(false);
    expect(result.violations.length).toBeGreaterThan(0);
  });

  it("no BLOCKER violations → passed=true even with warnings", () => {
    const ctx: ConstraintContext = {
      target_phase: "S4",
      phase_gates: { "S1-requirements": "APPROVED", "S2-architecture": "APPROVED" },
      tasks: [{ id: "T1", status: "active" }],
      gates: [{ id: "g1", status: "PASSED" }],
    };
    const result = hc.checkAll(ctx);
    // C6 blocks because current_phase is not S4, so C6 is skipped → passed
    expect(result.passed).toBe(true);
  });
});
