import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { initProject, loadState, checkGate, advanceGate, computeHash, validateProjectRoot, LoopError, migrateState, CURRENT_SCHEMA_VERSION } from "../src/core/state-machine.js";
import { submitEvidence, verifyEvidence } from "../src/core/evidence.js";
import { activateRole, completeRole, getRoleStatus } from "../src/core/role-engine.js";
import { createHandoff, getHandoffHistory } from "../src/core/handoff.js";
import { checkFreshness, checkCausalChain } from "../src/core/freshness.js";

const TEST_ROOT = join(process.cwd(), ".test-loop-tmp");

beforeEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
  mkdirSync(TEST_ROOT, { recursive: true });
});

afterEach(() => {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
});

describe("initProject", () => {
  it("creates state.yaml and gates.yaml", async () => {
    const state = await initProject(TEST_ROOT, "test-project");
    expect(state.project_name).toBe("test-project");
    expect(state.current_phase).toBe("requirements");
    expect(state.schema_version).toBe(1);
    expect(existsSync(join(TEST_ROOT, ".ai", "state.yaml"))).toBe(true);
    expect(existsSync(join(TEST_ROOT, ".ai", "gates.yaml"))).toBe(true);
  });
});

describe("loadState", () => {
  it("loads previously saved state", async () => {
    await initProject(TEST_ROOT, "load-test");
    const state = await loadState(TEST_ROOT);
    expect(state.project_name).toBe("load-test");
  });
});

// Finding "state-schema-no-migration": v1 states must load without leaving
// the v2-only optional fields as undefined.
describe("schema migration", () => {
  it("loadState normalizes a legacy v1 state and fills optional fields", async () => {
    const aiDir = join(TEST_ROOT, ".ai");
    mkdirSync(aiDir, { recursive: true });
    // Legacy v1 state.yaml WITHOUT loop_mode / project_status / iteration / user_approvals.
    const v1State = [
      "schema_version: 1",
      "project_name: legacy-project",
      "current_phase: requirements",
      "current_task_id: null",
      "current_gate_id: gate-requirements",
      "active_role: null",
      "role_activated_at: null",
      "completed_roles: []",
      "last_handoff_at: \"2026-01-01T00:00:00.000Z\"",
      "phases:",
      "  - phase_id: requirements",
      "    entered_at: \"2026-01-01T00:00:00.000Z\"",
      "    exited_at: null",
      "    status: active",
      "",
    ].join("\n");
    writeFileSync(join(aiDir, "state.yaml"), v1State, "utf-8");

    const state = await loadState(TEST_ROOT);
    // New optional fields must be defined (no undefined access).
    expect(state.loop_mode).toBe("STANDARD");
    expect(state.project_status).toBe("draft");
    expect(state.iteration).toBe(1);
    expect(state.user_approvals).toEqual({});
    // Legacy phase data is preserved, not destructively remapped.
    expect(state.current_phase).toBe("requirements");
    expect(state.phases.length).toBe(1);
    expect(state.phases[0].phase_id).toBe("requirements");
  });

  it("migrateState is idempotent and preserves existing v2 fields", () => {
    const now = new Date().toISOString();
    const v2 = {
      schema_version: 2,
      project_name: "ext",
      current_phase: "S1-requirements",
      current_task_id: null,
      current_gate_id: "gate-S1-requirements",
      active_role: null,
      role_activated_at: null,
      completed_roles: [],
      last_handoff_at: now,
      phases: [],
      loop_mode: "FULL" as const,
      project_status: "released" as const,
      iteration: 3,
    };
    const migrated = migrateState(v2);
    expect(migrated.schema_version).toBe(CURRENT_SCHEMA_VERSION);
    // Existing values are not overwritten.
    expect(migrated.loop_mode).toBe("FULL");
    expect(migrated.project_status).toBe("released");
    expect(migrated.iteration).toBe(3);
    expect(migrated.user_approvals).toEqual({});
    // Idempotent: migrating again yields the same shape.
    const again = migrateState(migrated);
    expect(again).toEqual(migrated);
  });

  it("migrateState handles a missing schema_version as v1", () => {
    const partial = {
      project_name: "no-version",
      current_phase: "requirements",
      current_task_id: null,
      current_gate_id: null,
      active_role: null,
      role_activated_at: null,
      completed_roles: [],
      last_handoff_at: "2026-01-01T00:00:00.000Z",
      phases: [],
    } as unknown as Parameters<typeof migrateState>[0];
    const migrated = migrateState(partial);
    expect(migrated.schema_version).toBe(CURRENT_SCHEMA_VERSION);
    expect(migrated.loop_mode).toBe("STANDARD");
    expect(migrated.iteration).toBe(1);
  });
});

describe("checkGate", () => {
  it("returns block for gate with unmet conditions", async () => {
    await initProject(TEST_ROOT, "gate-test");
    const result = await checkGate(TEST_ROOT, "gate-requirements");
    expect(result.status).toBe("block");
    expect(result.missing_conditions.length).toBeGreaterThan(0);
  });

  it("throws for unknown gate", async () => {
    await initProject(TEST_ROOT, "gate-test");
    await expect(checkGate(TEST_ROOT, "nonexistent")).rejects.toThrow("Gate not found");
  });
});

describe("advanceGate", () => {
  it("blocks when conditions not met", async () => {
    await initProject(TEST_ROOT, "advance-test");
    const result = await advanceGate(TEST_ROOT, "gate-requirements");
    expect(result.success).toBe(false);
    expect(result.error).toContain("blocked");
  });
});

describe("evidence", () => {
  it("submit and verify evidence", async () => {
    await initProject(TEST_ROOT, "ev-test");
    const submit = await submitEvidence(TEST_ROOT, {
      evidence_id: "test-ev-1",
      type: "test_result",
      content: "all tests passed",
      role_id: "R07",
    });
    expect(submit.success).toBe(true);
    expect(submit.content_hash).toBeTruthy();

    const verify = await verifyEvidence(TEST_ROOT, "test-ev-1");
    expect(verify.match).toBe(true);
    expect(verify.status).toBe("verified");
  });

  it("detects tampered evidence", async () => {
    await initProject(TEST_ROOT, "tamper-test");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "tamper-ev",
      type: "test_result",
      content: "original content",
    });

    // Tamper with the file
    const { writeFileSync } = await import("node:fs");
    const evFile = join(TEST_ROOT, ".ai", "evidence", "tamper-ev.yaml");
    const raw = (await import("node:fs")).readFileSync(evFile, "utf-8");
    writeFileSync(evFile, raw.replace("original content", "TAMPERED"), "utf-8");

    const verify = await verifyEvidence(TEST_ROOT, "tamper-ev");
    expect(verify.match).toBe(false);
    expect(verify.status).toBe("tampered");
  });
});

describe("computeHash", () => {
  it("produces consistent SHA-256", () => {
    const h1 = computeHash("hello");
    const h2 = computeHash("hello");
    expect(h1).toBe(h2);
    expect(h1).toHaveLength(64);
  });

  it("different inputs produce different hashes", () => {
    expect(computeHash("a")).not.toBe(computeHash("b"));
  });
});

describe("role engine", () => {
  it("activate and query role", async () => {
    await initProject(TEST_ROOT, "role-test");
    const result = await activateRole(TEST_ROOT, "R04");
    expect(result.success).toBe(true);
    expect(result.status).toBe("active");
  });
});

describe("freshness", () => {
  it("evidence without TTL is always fresh", async () => {
    await initProject(TEST_ROOT, "fresh-test");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "no-ttl-ev",
      type: "test_result",
      content: "data",
    });
    const result = await checkFreshness(TEST_ROOT, "no-ttl-ev");
    expect(result.status).toBe("no_ttl");
  });

  it("expired evidence is stale", async () => {
    await initProject(TEST_ROOT, "fresh-test");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "ttl-ev",
      type: "test_result",
      content: "data",
      ttl_seconds: 0, // Expires immediately
    });
    const result = await checkFreshness(TEST_ROOT, "ttl-ev");
    expect(result.status).toBe("stale");
  });
});

describe("causal chain", () => {
  it("valid chain with no dependencies", async () => {
    await initProject(TEST_ROOT, "chain-test");
    await submitEvidence(TEST_ROOT, {
      evidence_id: "root-ev",
      type: "test_result",
      content: "data",
    });
    const result = await checkCausalChain(TEST_ROOT, "root-ev");
    expect(result.valid).toBe(true);
    expect(result.broken_links).toHaveLength(0);
  });
});

describe("handoff", () => {
  it("creates handoff record", async () => {
    await initProject(TEST_ROOT, "handoff-test");
    const result = await createHandoff(
      TEST_ROOT, "R01", "R04",
      [{ path: "requirements.md", version: "1.0" }],
      "Requirements baselined",
    );
    expect(result.success).toBe(true);
    expect(result.artifacts_count).toBe(1);

    const history = getHandoffHistory(TEST_ROOT);
    expect(history).toContain("R01");
    expect(history).toContain("R04");
  });
});

// ── Regression tests for P0/P1 fixes ─────────────────────
describe("P0-C2: evidence_id path traversal", () => {
  it("rejects evidence_id with path separators", async () => {
    await initProject(TEST_ROOT, "path-traversal");
    await expect(submitEvidence(TEST_ROOT, {
      evidence_id: "../../etc/passwd",
      type: "test_result",
      content: "malicious",
    })).rejects.toThrow("invalid characters");
  });

  it("rejects evidence_id with dots", async () => {
    await initProject(TEST_ROOT, "path-traversal");
    await expect(verifyEvidence(TEST_ROOT, "../state")).rejects.toThrow("invalid characters");
  });
});

describe("P0-C3: roleId path traversal", () => {
  it("rejects roleId with path separators", async () => {
    await initProject(TEST_ROOT, "role-traversal");
    await expect(activateRole(TEST_ROOT, "../../etc/passwd")).rejects.toThrow("invalid characters");
  });
});

describe("P0-C4: validateProjectRoot", () => {
  it("rejects relative paths", () => {
    expect(() => validateProjectRoot("./relative")).toThrow("absolute");
  });

  it("rejects paths with ..", () => {
    expect(() => validateProjectRoot("/tmp/foo/../../etc")).toThrow("must not contain");
  });

  it("accepts valid absolute paths", () => {
    const result = validateProjectRoot(join(process.cwd(), "valid-root"));
    expect(result).toBeTruthy();
  });
});

describe("P0-C1: role_required checks completed_roles", () => {
  it("gate blocks when role not in completed_roles", async () => {
    await initProject(TEST_ROOT, "completed-roles");
    // Activate R01 but don't complete
    await activateRole(TEST_ROOT, "R01");
    const result = await checkGate(TEST_ROOT, "gate-requirements");
    // Should still be blocked because R01 is not in completed_roles
    expect(result.status).toBe("block");
  });

  it("gate passes role_required after completeRole", async () => {
    await initProject(TEST_ROOT, "completed-roles");
    await activateRole(TEST_ROOT, "R01");
    await completeRole(TEST_ROOT, "R01");
    const state = await loadState(TEST_ROOT);
    expect(state.completed_roles).toContain("R01");
    // Now submit evidence so evidence_required also passes
    await submitEvidence(TEST_ROOT, {
      evidence_id: "acceptance-ev",
      type: "acceptance_criteria",
      content: "criteria defined",
    });
    const result = await checkGate(TEST_ROOT, "gate-requirements");
    expect(result.status).toBe("pass");
  });
});

describe("P1-W1: evidence_required filters by type", () => {
  it("gate blocks when evidence type doesn't match", async () => {
    await initProject(TEST_ROOT, "type-filter");
    await activateRole(TEST_ROOT, "R01");
    await completeRole(TEST_ROOT, "R01");
    // Submit wrong type
    await submitEvidence(TEST_ROOT, {
      evidence_id: "wrong-type",
      type: "test_result",  // gate requires "acceptance_criteria"
      content: "data",
    });
    const result = await checkGate(TEST_ROOT, "gate-requirements");
    // role_required passes, but evidence_required for acceptance_criteria fails
    const evMissing = result.missing_conditions.find(c => c.condition_id === "acceptance-defined");
    expect(evMissing).toBeTruthy();
  });
});

describe("P1-W5: activated_at returns correct time", () => {
  it("returns stored activation time, not current time", async () => {
    await initProject(TEST_ROOT, "activated-at");
    const activateResult = await activateRole(TEST_ROOT, "R04");
    const statusResult = await getRoleStatus(TEST_ROOT, "R04");
    expect(statusResult.activated_at).toBe(activateResult.activated_at);
  });
});
