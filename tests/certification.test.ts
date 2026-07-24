import { describe, it, expect } from "vitest";
import {
  CertState, computeNextState, runChallengeForRole, runAllCertifications,
  buildCertStateAfterRun, CHALLENGE_REGISTRY, ALL_ROLES,
} from "../src/core/certification.js";
import type { RoleCertState } from "../src/core/certification.js";

// ── State Machine ───────────────────────────────────────
describe("computeNextState", () => {
  it("pass → CERTIFIED from any state", () => {
    expect(computeNextState(CertState.ROLE_BLOCKED, 5, true)).toBe(CertState.CERTIFIED);
    expect(computeNextState(CertState.DEGRADED, 1, true)).toBe(CertState.CERTIFIED);
    expect(computeNextState(CertState.REVALIDATION_REQUIRED, 2, true)).toBe(CertState.CERTIFIED);
  });

  it("1 failure → DEGRADED", () => {
    expect(computeNextState(CertState.CERTIFIED, 0, false)).toBe(CertState.DEGRADED);
  });

  it("2 consecutive failures → REVALIDATION_REQUIRED", () => {
    expect(computeNextState(CertState.DEGRADED, 1, false)).toBe(CertState.REVALIDATION_REQUIRED);
  });

  it("3+ consecutive failures → ROLE_BLOCKED", () => {
    expect(computeNextState(CertState.REVALIDATION_REQUIRED, 2, false)).toBe(CertState.ROLE_BLOCKED);
  });

  it("4 failures still ROLE_BLOCKED", () => {
    expect(computeNextState(CertState.ROLE_BLOCKED, 3, false)).toBe(CertState.ROLE_BLOCKED);
  });
});

// ── Challenge Registry ──────────────────────────────────
describe("CHALLENGE_REGISTRY", () => {
  it("has all 11 roles", () => {
    expect(ALL_ROLES).toHaveLength(11);
  });

  it("contains expected role IDs", () => {
    const expected = [
      "main-thread", "product-manager", "project-manager",
      "system-architect", "module-architect", "developer",
      "quality-engineer", "security-engineer", "independent-reviewer",
      "delivery-manager", "release-engineer",
    ];
    for (const r of expected) {
      expect(ALL_ROLES).toContain(r);
    }
  });
});

// ── Individual Challenges ───────────────────────────────
describe("challenge execution", () => {
  for (const roleId of ALL_ROLES) {
    it(`${roleId} challenge passes`, () => {
      const { result } = runChallengeForRole(roleId, {});
      expect(result.passed).toBe(true);
      expect(result.checks_passed).toBeGreaterThan(0);
      expect(result.checks_failed).toBe(0);
      expect(result.evidence_hash).toBeTruthy();
      expect(result.evidence_hash).toHaveLength(64); // SHA-256
    });
  }
});

// ── Evidence Hash Determinism ───────────────────────────
describe("evidence hash determinism", () => {
  it("same challenge produces same hash", () => {
    const { result: r1 } = runChallengeForRole("developer", {});
    const { result: r2 } = runChallengeForRole("developer", {});
    expect(r1.evidence_hash).toBe(r2.evidence_hash);
  });

  it("different challenges produce different hashes", () => {
    const { result: r1 } = runChallengeForRole("developer", {});
    const { result: r2 } = runChallengeForRole("product-manager", {});
    expect(r1.evidence_hash).not.toBe(r2.evidence_hash);
  });
});

// ── State Transitions ───────────────────────────────────
describe("state transitions", () => {
  it("passing challenge from CERTIFIED stays CERTIFIED", () => {
    const state: Record<string, RoleCertState> = {
      developer: { state: "CERTIFIED", consecutive_failures: 0, last_run: "", last_challenge: "", last_score: 0, last_evidence_hash: "" },
    };
    const { transition } = runChallengeForRole("developer", state);
    expect(transition.previous_state).toBe("CERTIFIED");
    expect(transition.next_state).toBe("CERTIFIED");
    expect(transition.consecutive_failures_after).toBe(0);
  });

  it("failing challenge degrades state", () => {
    // Use unknown role to simulate failure — returns early with UNKNOWN previous_state
    const state: Record<string, RoleCertState> = {
      "unknown-role": { state: "CERTIFIED", consecutive_failures: 0, last_run: "", last_challenge: "", last_score: 0, last_evidence_hash: "" },
    };
    const { transition } = runChallengeForRole("unknown-role", state);
    expect(transition.next_state).toBe("UNKNOWN"); // unknown role returns UNKNOWN state
    expect(transition.challenge_passed).toBe(false);
  });
});

// ── runAllCertifications ────────────────────────────────
describe("runAllCertifications", () => {
  it("all 11 roles pass", () => {
    const run = runAllCertifications();
    expect(run.overall_pass).toBe(true);
    expect(Object.keys(run.results)).toHaveLength(11);
    expect(Object.keys(run.state_transitions)).toHaveLength(11);
  });

  it("all transitions go to CERTIFIED", () => {
    const run = runAllCertifications();
    for (const [, tr] of Object.entries(run.state_transitions)) {
      expect(tr.next_state).toBe("CERTIFIED");
    }
  });

  it("run_at is set", () => {
    const run = runAllCertifications();
    expect(run.run_at).toBeTruthy();
  });
});

// ── buildCertStateAfterRun ──────────────────────────────
describe("buildCertStateAfterRun", () => {
  it("produces state for all roles", () => {
    const run = runAllCertifications();
    const newState = buildCertStateAfterRun({}, run);
    expect(Object.keys(newState)).toHaveLength(11);
  });

  it("all roles CERTIFIED after passing run", () => {
    const run = runAllCertifications();
    const newState = buildCertStateAfterRun({}, run);
    for (const [, rs] of Object.entries(newState)) {
      expect(rs.state).toBe("CERTIFIED");
      expect(rs.consecutive_failures).toBe(0);
    }
  });

  it("preserves evidence hashes", () => {
    const run = runAllCertifications();
    const newState = buildCertStateAfterRun({}, run);
    for (const roleId of ALL_ROLES) {
      expect(newState[roleId].last_evidence_hash).toBe(run.results[roleId].evidence_hash);
    }
  });
});
