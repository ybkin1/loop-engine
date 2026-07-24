import { describe, it, expect } from "vitest";
import { VetoEscalation, VetoSeverity, EscalationLevel } from "../src/core/veto_escalation.js";
import type { VetoRecord } from "../src/core/veto_escalation.js";

const ve = new VetoEscalation();

function veto(roleId: string, severity: VetoSeverity = VetoSeverity.BLOCKER, reason = "test"): VetoRecord {
  return {
    veto_id: `veto-${roleId}-${Date.now()}`,
    role_id: roleId,
    severity,
    target: "test-operation",
    reason,
    created_at: new Date().toISOString(),
    resolved: false,
  };
}

// ── Single Role ────────────────────────────────────────
describe("VetoEscalation", () => {
  it("single role BLOCKER → ROLE_INTERNAL", () => {
    const result = ve.checkEscalation([veto("R06")]);
    expect(result.level).toBe(EscalationLevel.ROLE_INTERNAL);
  });

  // ── Multiple Roles Same Domain ─────────────────────────
  it("2 roles same domain → CROSS_ROLE", () => {
    // R04=architecture, R05=architecture
    const result = ve.checkEscalation([veto("R04"), veto("R05")]);
    expect(result.level).toBe(EscalationLevel.CROSS_ROLE);
  });

  // ── Multiple Roles Different Domains ───────────────────
  it("2 roles different domains → CROSS_ROLE", () => {
    // R06=engineering, R07=quality
    const result = ve.checkEscalation([veto("R06"), veto("R07")]);
    expect(result.level).toBe(EscalationLevel.CROSS_ROLE);
  });

  // ── Security Role Involved ─────────────────────────────
  it("R08(security) + R06(development) → USER_GATE (immediate)", () => {
    const result = ve.checkEscalation([veto("R08"), veto("R06")]);
    expect(result.level).toBe(EscalationLevel.USER_GATE);
    expect(result.human_review_needed).toBe(true);
  });

  // ── 3+ Roles ─────────────────────────────────────────
  it("≥3 roles involved → USER_GATE", () => {
    // R04=architecture, R06=engineering, R07=quality
    const result = ve.checkEscalation([veto("R04"), veto("R06"), veto("R07")]);
    expect(result.level).toBe(EscalationLevel.USER_GATE);
    expect(result.human_review_needed).toBe(true);
  });

  // ── All WARNING ──────────────────────────────────────
  it("all WARNING → ROLE_INTERNAL (single role)", () => {
    const result = ve.checkEscalation([veto("R06", VetoSeverity.WARNING)]);
    expect(result.level).toBe(EscalationLevel.ROLE_INTERNAL);
  });

  // ── generateHumanReviewSummary ───────────────────────
  it("generateHumanReviewSummary outputs non-empty string", () => {
    const vetoes = [veto("R06"), veto("R08")];
    const summary = ve.generateHumanReviewSummary(vetoes);
    expect(typeof summary).toBe("string");
    expect(summary.length).toBeGreaterThan(0);
    expect(summary).toContain("Veto Review Summary");
    expect(summary).toContain("R06");
    expect(summary).toContain("R08");
  });
});
