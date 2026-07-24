import { describe, test, expect, afterAll, beforeAll } from "vitest";
import { spawnSync } from "node:child_process";
import { writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { createRequire } from "node:module";

const HOOKS_DIR = join(__dirname, "..", "..", "hooks", "scripts");
const TEMP_DIR = join(__dirname, "..", ".test-temp-hooks");

// ── Helper: run a hook script via child_process ──────────────────────
function runHook(
  scriptName: string,
  event: object,
): { exitCode: number; stderr: string; stdout: string } {
  const scriptPath = join(HOOKS_DIR, scriptName);
  const result = spawnSync("node", [`"${scriptPath}"`], {
    input: JSON.stringify(event),
    encoding: "utf-8",
    timeout: 5000,
    shell: true,
    env: { ...process.env },
  });
  return {
    exitCode: result.status ?? 1,
    stderr: result.stderr || "",
    stdout: result.stdout || "",
  };
}

// ── Helper: create a temporary project structure ─────────────────────
function setupTempProject(files: Record<string, string>) {
  if (existsSync(TEMP_DIR)) rmSync(TEMP_DIR, { recursive: true });
  mkdirSync(TEMP_DIR, { recursive: true });
  for (const [relPath, content] of Object.entries(files)) {
    const fullPath = join(TEMP_DIR, relPath);
    const dir = dirname(fullPath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(fullPath, content);
  }
}

// ── Load hook_common.js via createRequire (CJS in ESM context) ──────
const require_ = createRequire(import.meta.url);
const common = require_("../../hooks/scripts/hook_common.js") as {
  isReadonlyCommand: (cmd: string) => boolean;
  isGovernanceFile: (filePath: string, root: string) => boolean;
  extractYamlValue: (content: string, key: string) => string | null;
  extractYamlList: (content: string, key: string) => string[];
  phaseToPaths: (phase: string) => string[];
  isPathInPhase: (relativePath: string, phase: string) => boolean;
};

// ── Cleanup ──────────────────────────────────────────────────────────
afterAll(() => {
  if (existsSync(TEMP_DIR)) rmSync(TEMP_DIR, { recursive: true });
});

// ════════════════════════════════════════════════════════════════════
//  hook_common.js  —  direct unit tests
// ════════════════════════════════════════════════════════════════════
describe("hook_common.js", () => {
  // ── isReadonlyCommand ────────────────────────────────────────────
  describe("isReadonlyCommand", () => {
    test("npm test → true", () => {
      expect(common.isReadonlyCommand("npm test")).toBe(true);
    });

    test("git status → true", () => {
      expect(common.isReadonlyCommand("git status")).toBe(true);
    });

    test("git log → true", () => {
      expect(common.isReadonlyCommand("git log")).toBe(true);
    });

    test("git diff → true", () => {
      expect(common.isReadonlyCommand("git diff")).toBe(true);
    });

    test("cat file.txt → true", () => {
      expect(common.isReadonlyCommand("cat file.txt")).toBe(true);
    });

    test("ls -la → true", () => {
      expect(common.isReadonlyCommand("ls -la")).toBe(true);
    });

    test("npx eslint src/ → true", () => {
      expect(common.isReadonlyCommand("npx eslint src/")).toBe(true);
    });

    test("rm -rf / → false", () => {
      expect(common.isReadonlyCommand("rm -rf /")).toBe(false);
    });

    test("git commit -m 'test' → false", () => {
      expect(common.isReadonlyCommand("git commit -m 'test'")).toBe(false);
    });

    test("npm publish → false", () => {
      expect(common.isReadonlyCommand("npm publish")).toBe(false);
    });

    test("npm install → false", () => {
      expect(common.isReadonlyCommand("npm install")).toBe(false);
    });

    test("git push → false", () => {
      expect(common.isReadonlyCommand("git push")).toBe(false);
    });

    test("mkdir foo → false", () => {
      expect(common.isReadonlyCommand("mkdir foo")).toBe(false);
    });

    test("echo hello > file.txt → false (redirect)", () => {
      expect(common.isReadonlyCommand("echo hello > file.txt")).toBe(false);
    });

    test("empty string → true", () => {
      expect(common.isReadonlyCommand("")).toBe(true);
    });
  });

  // ── isGovernanceFile ─────────────────────────────────────────────
  describe("isGovernanceFile", () => {
    test(".ai/state.yaml → true", () => {
      expect(common.isGovernanceFile(".ai/state.yaml", "/project")).toBe(true);
    });

    test(".ai/gates.yaml → true", () => {
      expect(common.isGovernanceFile(".ai/gates.yaml", "/project")).toBe(true);
    });

    test(".ai/ledger/audit.jsonl → true", () => {
      expect(common.isGovernanceFile(".ai/ledger/audit.jsonl", "/project")).toBe(true);
    });

    test("src/main.ts → false", () => {
      expect(common.isGovernanceFile("src/main.ts", "/project")).toBe(false);
    });

    test("docs/readme.md → false", () => {
      expect(common.isGovernanceFile("docs/readme.md", "/project")).toBe(false);
    });

    test("empty path → false", () => {
      expect(common.isGovernanceFile("", "/project")).toBe(false);
    });
  });

  // ── extractYamlValue ─────────────────────────────────────────────
  describe("extractYamlValue", () => {
    test("simple key", () => {
      expect(common.extractYamlValue("name: test\nvalue: 42", "name")).toBe("test");
    });

    test("numeric value", () => {
      expect(common.extractYamlValue("name: test\nvalue: 42", "value")).toBe("42");
    });

    test("quoted value", () => {
      expect(common.extractYamlValue('title: "hello world"', "title")).toBe("hello world");
    });

    test("missing key → null", () => {
      expect(common.extractYamlValue("name: test", "missing")).toBeNull();
    });

    test("null value → null", () => {
      expect(common.extractYamlValue("key: null", "key")).toBeNull();
    });
  });

  // ── extractYamlList ──────────────────────────────────────────────
  describe("extractYamlList", () => {
    test("inline array", () => {
      expect(common.extractYamlList("paths: [src, lib]", "paths")).toEqual(["src", "lib"]);
    });

    test("YAML list format", () => {
      const yaml = "items:\n  - alpha\n  - beta\n  - gamma\n";
      expect(common.extractYamlList(yaml, "items")).toEqual(["alpha", "beta", "gamma"]);
    });

    test("missing key → empty array", () => {
      expect(common.extractYamlList("other: [a]", "missing")).toEqual([]);
    });
  });

  // ── phaseToPaths ─────────────────────────────────────────────────
  describe("phaseToPaths", () => {
    test("P4 → src/, lib/, tests/, test/", () => {
      const paths = common.phaseToPaths("P4");
      expect(paths).toContain("src/");
      expect(paths).toContain("lib/");
      expect(paths).toContain("tests/");
      expect(paths).toContain("test/");
    });

    test("P1 → docs paths", () => {
      const paths = common.phaseToPaths("P1");
      expect(paths.some((p: string) => p.startsWith("docs/"))).toBe(true);
    });

    test("P2 → architecture docs", () => {
      const paths = common.phaseToPaths("P2");
      expect(paths).toContain("docs/architecture");
    });

    test("empty phase → empty array", () => {
      expect(common.phaseToPaths("")).toEqual([]);
    });
  });

  // ── isPathInPhase ────────────────────────────────────────────────
  describe("isPathInPhase", () => {
    test("src/main.ts in P4 → true", () => {
      expect(common.isPathInPhase("src/main.ts", "P4")).toBe(true);
    });

    test("tests/unit.test.ts in P4 → true", () => {
      expect(common.isPathInPhase("tests/unit.test.ts", "P4")).toBe(true);
    });

    test("lib/utils.js in P4 → true", () => {
      expect(common.isPathInPhase("lib/utils.js", "P4")).toBe(true);
    });

    test("docs/readme.md in P4 → false", () => {
      expect(common.isPathInPhase("docs/readme.md", "P4")).toBe(false);
    });

    test("docs/architecture/adr.md in P2 → true", () => {
      expect(common.isPathInPhase("docs/architecture/adr.md", "P2")).toBe(true);
    });

    test("src/main.ts in P1 → false", () => {
      expect(common.isPathInPhase("src/main.ts", "P1")).toBe(false);
    });
  });
});

// ════════════════════════════════════════════════════════════════════
//  gate-guard.js  —  integration tests via child_process
// ════════════════════════════════════════════════════════════════════
describe("gate-guard.js", () => {
  test("非治理项目 → exit 0 (no .ai/ directory)", () => {
    const result = runHook("gate-guard.js", {
      cwd: "/tmp/non-governance-project",
      tool_name: "Write",
      tool_input: { file_path: "/tmp/non-governance-project/src/main.ts" },
    });
    expect(result.exitCode).toBe(0);
  });

  test("Loop 未激活 → exit 0 (phase=S0-init)", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: S0-init\n",
      ".ai/gates.yaml": "gates: []\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("治理文件 → exit 0 (.ai/state.yaml always allowed)", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PENDING\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, ".ai/state.yaml") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("PENDING gate + phase-related path → exit 2", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PENDING\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(2);
    expect(result.stderr).toContain("PENDING");
  });

  test("PENDING gate + unrelated path → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PENDING\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "docs/readme.md") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("Bash readonly command (npm test) → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PENDING\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Bash",
      tool_input: { command: "npm test" },
    });
    expect(result.exitCode).toBe(0);
  });

  test("非写入操作 (Read) → exit 0", () => {
    const result = runHook("gate-guard.js", {
      cwd: "/tmp/any-project",
      tool_name: "Read",
      tool_input: { file_path: "/tmp/some-file.ts" },
    });
    expect(result.exitCode).toBe(0);
  });

  test("BLOCKED gate → exit 2", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: BLOCKED\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(2);
    expect(result.stderr).toContain("BLOCKED");
  });

  test("no gates pending/blocked → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\ncurrent_phase: P4-implementation\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PASSED\n    phase: P4\n",
    });
    const result = runHook("gate-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(0);
  });
});

// ════════════════════════════════════════════════════════════════════
//  path-guard.js  —  integration tests via child_process
// ════════════════════════════════════════════════════════════════════
describe("path-guard.js", () => {
  test("非治理项目 → exit 0", () => {
    const result = runHook("path-guard.js", {
      cwd: "/tmp/non-gov",
      tool_name: "Write",
      tool_input: { file_path: "/tmp/non-gov/src/main.ts" },
    });
    expect(result.exitCode).toBe(0);
  });

  test("治理文件 → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\n",
      ".ai/contracts.yaml": "allowed_write: [src]\n",
    });
    const result = runHook("path-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, ".ai/state.yaml") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("contracts.yaml 不存在 → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\n",
    });
    const result = runHook("path-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("路径在 allowed_write 内 → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\n",
      ".ai/contracts.yaml": "allowed_write: [src, lib]\n",
    });
    const result = runHook("path-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "src/main.ts") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("路径在 allowed_write 外 → exit 2", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\n",
      ".ai/contracts.yaml": "allowed_write: [src]\n",
    });
    const result = runHook("path-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Write",
      tool_input: { file_path: join(TEMP_DIR, "docs/readme.md") },
    });
    expect(result.exitCode).toBe(2);
    expect(result.stderr).toContain("outside allowed paths");
  });

  test("非写入操作 → exit 0", () => {
    setupTempProject({
      ".ai/state.yaml": "project_name: test\n",
      ".ai/contracts.yaml": "allowed_write: [src]\n",
    });
    const result = runHook("path-guard.js", {
      cwd: TEMP_DIR,
      tool_name: "Read",
      tool_input: { file_path: join(TEMP_DIR, "docs/readme.md") },
    });
    expect(result.exitCode).toBe(0);
  });
});

// ════════════════════════════════════════════════════════════════════
//  session-brief.js  —  integration tests via child_process
// ════════════════════════════════════════════════════════════════════
describe("session-brief.js", () => {
  test("非治理项目 → exit 0, no stdout", () => {
    const result = runHook("session-brief.js", {
      cwd: "/tmp/non-gov",
    });
    expect(result.exitCode).toBe(0);
    expect(result.stdout.trim()).toBe("");
  });

  test("治理项目 Loop 活跃 → stdout contains Loop Status", () => {
    setupTempProject({
      ".ai/state.yaml":
        "project_name: TestProject\ncurrent_phase: P4-implementation\ncurrent_gate_id: G1\n",
      ".ai/gates.yaml":
        "gates:\n  - gate_id: G1\n    status: PASSED\n    phase: P4\n",
    });
    const result = runHook("session-brief.js", {
      cwd: TEMP_DIR,
    });
    expect(result.exitCode).toBe(0);
    // Output is JSON wrapping additionalContext
    const output = JSON.parse(result.stdout);
    const context = output.hookSpecificOutput.additionalContext;
    expect(context).toContain("Loop Engineering Status");
    expect(context).toContain("TestProject");
  });

  test("治理项目 Loop 未激活 → stdout contains inactive message", () => {
    setupTempProject({
      ".ai/state.yaml":
        "project_name: InactiveProject\ncurrent_phase: S0-init\n",
      ".ai/gates.yaml": "gates: []\n",
    });
    const result = runHook("session-brief.js", {
      cwd: TEMP_DIR,
    });
    expect(result.exitCode).toBe(0);
    // Loop inactive but governance project exists → still outputs context
    const output = JSON.parse(result.stdout);
    const context = output.hookSpecificOutput.additionalContext;
    expect(context).toContain("Loop Engineering Status");
    expect(context).toContain("InactiveProject");
  });
});
