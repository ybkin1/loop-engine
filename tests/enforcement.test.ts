import { describe, it, expect } from "vitest";
import {
  EnforcementLevel, deriveEnforcementLevel, validateHostCapabilities,
  checkConstraint, getDegradationTable, HARD_CONSTRAINTS, HOST_PRESETS,
} from "../src/core/enforcement.js";
import type { HostCapabilities } from "../src/core/enforcement.js";

// ── deriveEnforcementLevel ──────────────────────────────
describe("deriveEnforcementLevel", () => {
  it("returns STRONG when all capabilities present", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: true, can_intercept_commands: true,
      can_isolate_agents: true, can_enforce_exit_codes: true, has_hooks_api: true,
    };
    expect(deriveEnforcementLevel(caps)).toBe(EnforcementLevel.STRONG);
  });

  it("returns MEDIUM when has_hooks_api but no write intercept", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: false, can_intercept_commands: false,
      can_isolate_agents: false, can_enforce_exit_codes: false, has_hooks_api: true,
    };
    expect(deriveEnforcementLevel(caps)).toBe(EnforcementLevel.MEDIUM);
  });

  it("returns MEDIUM when can_isolate_agents but no hooks", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: false, can_intercept_commands: false,
      can_isolate_agents: true, can_enforce_exit_codes: false, has_hooks_api: false,
    };
    expect(deriveEnforcementLevel(caps)).toBe(EnforcementLevel.MEDIUM);
  });

  it("returns ADVISORY when no capabilities", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: false, can_intercept_commands: false,
      can_isolate_agents: false, can_enforce_exit_codes: false, has_hooks_api: false,
    };
    expect(deriveEnforcementLevel(caps)).toBe(EnforcementLevel.ADVISORY);
  });

  it("returns STRONG for partial but sufficient capabilities", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: true, can_intercept_commands: true,
      can_isolate_agents: false, can_enforce_exit_codes: true, has_hooks_api: false,
    };
    expect(deriveEnforcementLevel(caps)).toBe(EnforcementLevel.STRONG);
  });
});

// ── validateHostCapabilities ────────────────────────────
describe("validateHostCapabilities", () => {
  it("no violations when claimed level matches actual", () => {
    const caps = HOST_PRESETS.zcode;
    const result = validateHostCapabilities(caps, EnforcementLevel.STRONG);
    expect(result.violations).toHaveLength(0);
    expect(result.is_honest).toBe(true);
  });

  it("detects when host claims STRONG but only supports MEDIUM", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: false, can_intercept_commands: false,
      can_isolate_agents: true, can_enforce_exit_codes: false, has_hooks_api: false,
    };
    const result = validateHostCapabilities(caps, EnforcementLevel.STRONG);
    expect(result.violations.length).toBeGreaterThan(0);
    expect(result.violations[0]).toContain("pretend");
  });

  it("does not block at ADVISORY even with violations", () => {
    const caps: HostCapabilities = {
      can_intercept_writes: false, can_intercept_commands: false,
      can_isolate_agents: true, can_enforce_exit_codes: false, has_hooks_api: false,
    };
    const result = validateHostCapabilities(caps, EnforcementLevel.STRONG);
    expect(result.is_blocked).toBe(false); // Only blocks at STRONG
  });
});

// ── checkConstraint ─────────────────────────────────────
describe("checkConstraint", () => {
  it("returns BLOCK for NO_IMPL_WITHOUT_REQUIREMENTS at STRONG", () => {
    const result = checkConstraint("NO_IMPL_WITHOUT_REQUIREMENTS", EnforcementLevel.STRONG, {
      phase: "implementation", requirements_baselined: false,
    });
    expect(result.action).toBe("BLOCK");
    expect(result.passed).toBe(false);
  });

  it("passes when requirements are baselined", () => {
    const result = checkConstraint("NO_IMPL_WITHOUT_REQUIREMENTS", EnforcementLevel.STRONG, {
      phase: "implementation", requirements_baselined: true,
    });
    expect(result.passed).toBe(true);
  });

  it("returns WARN at MEDIUM for same constraint", () => {
    const result = checkConstraint("NO_IMPL_WITHOUT_REQUIREMENTS", EnforcementLevel.MEDIUM, {
      phase: "implementation", requirements_baselined: false,
    });
    expect(result.action).toBe("WARN");
  });

  it("returns ADVISORY at ADVISORY level", () => {
    const result = checkConstraint("NO_WRITE_WITHOUT_TASK", EnforcementLevel.ADVISORY, {
      has_active_task: false, target_in_allowed_paths: false,
    });
    expect(result.action).toBe("ADVISORY");
  });

  it("NO_AUTO_GATE_PASS blocks at STRONG and MEDIUM", () => {
    const ctx = { gate_status: "approved", explicit_user_approval: false };
    const strong = checkConstraint("NO_AUTO_GATE_PASS", EnforcementLevel.STRONG, ctx);
    const medium = checkConstraint("NO_AUTO_GATE_PASS", EnforcementLevel.MEDIUM, ctx);
    expect(strong.action).toBe("BLOCK");
    expect(medium.action).toBe("BLOCK");
  });

  it("NO_AUTO_GATE_PASS warns at ADVISORY", () => {
    const ctx = { gate_status: "approved", explicit_user_approval: false };
    const result = checkConstraint("NO_AUTO_GATE_PASS", EnforcementLevel.ADVISORY, ctx);
    expect(result.action).toBe("WARN");
  });

  it("unknown constraint throws Error", () => {
    expect(() => checkConstraint("NONEXISTENT", EnforcementLevel.STRONG, {})).toThrow(/Unknown constraint/);
  });

  it("EVIDENCE_STALE_ON_CHANGE detects stale evidence", () => {
    const result = checkConstraint("EVIDENCE_STALE_ON_CHANGE", EnforcementLevel.STRONG, {
      evidence_is_stale: true,
    });
    expect(result.passed).toBe(false);
  });
});

// ── getDegradationTable ─────────────────────────────────
describe("getDegradationTable", () => {
  it("returns all 8 constraints", () => {
    const table = getDegradationTable(EnforcementLevel.STRONG);
    expect(table).toHaveLength(HARD_CONSTRAINTS.length);
  });

  it("STRONG can enforce all constraints", () => {
    const table = getDegradationTable(EnforcementLevel.STRONG);
    const enforceable = table.filter(t => t.can_enforce);
    expect(enforceable.length).toBe(HARD_CONSTRAINTS.length);
  });

  it("ADVISORY cannot enforce any constraint", () => {
    const table = getDegradationTable(EnforcementLevel.ADVISORY);
    const enforceable = table.filter(t => t.can_enforce);
    expect(enforceable.length).toBe(0);
  });
});

// ── HOST_PRESETS ────────────────────────────────────────
describe("HOST_PRESETS", () => {
  it("qoder is STRONG (PreToolUse hooks intercept writes + commands)", () => {
    expect(deriveEnforcementLevel(HOST_PRESETS.qoder)).toBe(EnforcementLevel.STRONG);
  });

  it("zcode is STRONG", () => {
    expect(deriveEnforcementLevel(HOST_PRESETS.zcode)).toBe(EnforcementLevel.STRONG);
  });

  it("claude_code is STRONG", () => {
    expect(deriveEnforcementLevel(HOST_PRESETS.claude_code)).toBe(EnforcementLevel.STRONG);
  });

  it("standalone is ADVISORY", () => {
    expect(deriveEnforcementLevel(HOST_PRESETS.standalone)).toBe(EnforcementLevel.ADVISORY);
  });
});
