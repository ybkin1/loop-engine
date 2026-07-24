import { describe, it, expect } from "vitest";
import {
  LoopMode, RiskLevel, routeIntent, defaultProfile,
} from "../src/core/router.js";
import type { ProjectProfile } from "../src/core/router.js";

function makeProfile(overrides: Partial<ProjectProfile> = {}): ProjectProfile {
  return { ...defaultProfile(), ...overrides };
}

// ── Risk Level Calculation ──────────────────────────────
describe("routeIntent — risk levels", () => {
  it("LOW risk when no factors", () => {
    const result = routeIntent(makeProfile());
    expect(result.risk_level).toBe(RiskLevel.LOW);
    expect(result.mode).toBe(LoopMode.LIGHTWEIGHT);
  });

  it("MEDIUM risk with 1 medium factor", () => {
    const result = routeIntent(makeProfile({ has_multiple_modules: true }));
    expect(result.risk_level).toBe(RiskLevel.MEDIUM);
    expect(result.mode).toBe(LoopMode.STANDARD);
  });

  it("HIGH risk with 1 high factor", () => {
    const result = routeIntent(makeProfile({ has_database: true }));
    expect(result.risk_level).toBe(RiskLevel.HIGH);
    expect(result.mode).toBe(LoopMode.FULL);
  });

  it("HIGH risk with 3+ medium factors", () => {
    const result = routeIntent(makeProfile({
      has_multiple_modules: true, has_external_api: true, requires_deployment: true,
    }));
    expect(result.risk_level).toBe(RiskLevel.HIGH);
    expect(result.mode).toBe(LoopMode.FULL);
  });

  it("CRITICAL risk with 2+ high factors", () => {
    const result = routeIntent(makeProfile({
      has_database: true, has_auth_permissions: true,
    }));
    expect(result.risk_level).toBe(RiskLevel.CRITICAL);
    expect(result.mode).toBe(LoopMode.FULL);
  });

  it("CRITICAL with all high factors", () => {
    const result = routeIntent(makeProfile({
      has_database: true, has_auth_permissions: true,
      has_payments: true, has_production_data: true, has_security_requirements: true,
    }));
    expect(result.risk_level).toBe(RiskLevel.CRITICAL);
  });
});

// ── Mode Routing ────────────────────────────────────────
describe("routeIntent — mode phases", () => {
  it("LIGHTWEIGHT has 3 phases", () => {
    const result = routeIntent(makeProfile());
    expect(result.phases).toHaveLength(3);
    expect(result.phases).toContain("requirements");
    expect(result.phases).toContain("implementation");
    expect(result.phases).toContain("delivery");
  });

  it("STANDARD has 6 phases", () => {
    const result = routeIntent(makeProfile({ has_multiple_modules: true }));
    expect(result.phases).toHaveLength(6);
    expect(result.phases).toContain("architecture");
    expect(result.phases).toContain("review");
  });

  it("FULL has 6 phases", () => {
    const result = routeIntent(makeProfile({ has_database: true }));
    expect(result.phases).toHaveLength(6);
  });
});

// ── User Override ───────────────────────────────────────
describe("routeIntent — user override", () => {
  it("user can force FULL mode even for low-risk project", () => {
    const result = routeIntent(makeProfile({ user_forced_mode: LoopMode.FULL }));
    expect(result.mode).toBe(LoopMode.FULL);
    expect(result.reason).toContain("User forced");
  });

  it("user can force LIGHTWEIGHT even for high-risk project", () => {
    const result = routeIntent(makeProfile({
      has_database: true, has_payments: true,
      user_forced_mode: LoopMode.LIGHTWEIGHT,
    }));
    expect(result.mode).toBe(LoopMode.LIGHTWEIGHT);
    // But risk level still reflects reality
    expect(result.risk_level).toBe(RiskLevel.CRITICAL);
  });

  it("user override preserves risk factor reporting", () => {
    const result = routeIntent(makeProfile({
      has_database: true, has_multiple_modules: true,
      user_forced_mode: LoopMode.STANDARD,
    }));
    expect(result.high_risk_factors).toContain("has_database");
    expect(result.medium_risk_factors).toContain("has_multiple_modules");
  });
});

// ── Reason String ───────────────────────────────────────
describe("routeIntent — reason", () => {
  it("includes high-risk factor names", () => {
    const result = routeIntent(makeProfile({ has_database: true }));
    expect(result.reason).toContain("has_database");
  });

  it("includes medium-risk factor names", () => {
    const result = routeIntent(makeProfile({ has_external_api: true }));
    expect(result.reason).toContain("has_external_api");
  });

  it("says 'no risk factors' when clean", () => {
    const result = routeIntent(makeProfile());
    expect(result.reason).toContain("no risk factors");
  });
});

// ── defaultProfile ──────────────────────────────────────
describe("defaultProfile", () => {
  it("all factors false", () => {
    const p = defaultProfile();
    expect(p.has_database).toBe(false);
    expect(p.has_auth_permissions).toBe(false);
    expect(p.user_forced_mode).toBeNull();
  });
});
