import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdirSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const HOOKS_DIR = join(__dirname, "..", "..", "hooks", "scripts");
const GATE_GUARD = join(HOOKS_DIR, "gate-guard.js");
const PATH_GUARD = join(HOOKS_DIR, "path-guard.js");
const TEST_ROOT = join(process.cwd(), ".test-bypass-tmp");

function runHook(
  scriptPath: string,
  input: object,
  cwd?: string,
): { exitCode: number; stderr: string; stdout: string } {
  const result = spawnSync("node", [`"${scriptPath}"`], {
    input: JSON.stringify(input),
    encoding: "utf-8",
    timeout: 5000,
    shell: true,
    cwd: cwd || TEST_ROOT,
  });
  return {
    exitCode: result.status ?? 1,
    stderr: result.stderr ?? "",
    stdout: result.stdout ?? "",
  };
}

function setupDir() {
  if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true });
  mkdirSync(TEST_ROOT, { recursive: true });
  mkdirSync(join(TEST_ROOT, ".ai"), { recursive: true });
  // state.yaml required for isGovernanceProject + isLoopActive
  writeFileSync(
    join(TEST_ROOT, ".ai", "state.yaml"),
    "project_name: test\ncurrent_phase: implementation\ncurrent_gate_id: gate-impl\n",
    "utf-8",
  );
}

function writeGates(status: string) {
  const content = [
    "gates:",
    "  - gate_id: gate-impl",
    "    phase: implementation",
    `    status: ${status}`,
    "",
  ].join("\n");
  writeFileSync(join(TEST_ROOT, ".ai", "gates.yaml"), content, "utf-8");
}

function writeContracts(allowedPaths: string[]) {
  const paths = allowedPaths.map(p => `"${p}"`).join(", ");
  const content = `allowed_write: [${paths}]\n`;
  writeFileSync(join(TEST_ROOT, ".ai", "contracts.yaml"), content, "utf-8");
}

beforeAll(() => setupDir());
afterAll(() => { if (existsSync(TEST_ROOT)) rmSync(TEST_ROOT, { recursive: true }); });

// ════════════════════════════════════════════════════════
// Bash Command Bypass Detection (gate-guard.js)
// ════════════════════════════════════════════════════════
describe("Bash command bypass detection", () => {
  describe("write commands should be detected", () => {
    const writeCommands = [
      { cmd: "echo test > file.txt", label: "echo redirect" },
      { cmd: "touch newfile.txt", label: "touch" },
      { cmd: "mkdir -p src/components", label: "mkdir" },
      { cmd: "cp src/a.ts src/b.ts", label: "cp" },
      { cmd: "mv old.ts new.ts", label: "mv" },
      { cmd: "git commit -m 'test'", label: "git commit" },
      { cmd: "git push origin main", label: "git push" },
      { cmd: "npm publish", label: "npm publish" },
      { cmd: "rm -rf node_modules", label: "rm -rf" },
    ];

    for (const { cmd, label } of writeCommands) {
      it(`detects write: ${label}`, () => {
        setupDir();
        writeGates("PENDING");
        const result = runHook(GATE_GUARD, {
          tool_name: "Bash",
          tool_input: { command: cmd },
          cwd: TEST_ROOT,
        });
        expect(result.exitCode).toBe(2);
      });
    }
  });

  describe("read-only commands should pass", () => {
    const readOnlyCommands = [
      { cmd: "npm test", label: "npm test" },
      { cmd: "npx eslint src/", label: "npx eslint" },
      { cmd: "npx tsc --noEmit", label: "npx tsc --noEmit" },
      { cmd: "git status", label: "git status" },
      { cmd: "git log --oneline", label: "git log" },
      { cmd: "git diff HEAD", label: "git diff" },
      { cmd: "ls -la", label: "ls" },
      { cmd: "cat package.json", label: "cat" },
    ];

    for (const { cmd, label } of readOnlyCommands) {
      it(`allows read-only: ${label}`, () => {
        setupDir();
        writeGates("PENDING");
        const result = runHook(GATE_GUARD, {
          tool_name: "Bash",
          tool_input: { command: cmd },
          cwd: TEST_ROOT,
        });
        expect(result.exitCode).toBe(0);
      });
    }
  });
});

// ════════════════════════════════════════════════════════
// Path Bypass Detection (path-guard.js)
// ════════════════════════════════════════════════════════
describe("Path bypass detection", () => {
  const blockedPaths = [
    { path: "C:\\Windows\\System32\\config", label: "system root outside project" },
    { path: "../../etc/passwd", label: "directory traversal" },
    { path: "C:\\Users\\Admin\\secrets.txt", label: "absolute path outside project" },
  ];

  for (const { path: p, label } of blockedPaths) {
    it(`blocks: ${label}`, () => {
      setupDir();
      writeContracts(["src/", "tests/"]);
      const result = runHook(PATH_GUARD, {
        tool_name: "Write",
        tool_input: { file_path: p },
        cwd: TEST_ROOT,
      }, TEST_ROOT);
      expect(result.exitCode).toBe(2);
    });
  }

  it("allows: src/index.ts (inside project root)", () => {
    setupDir();
    writeContracts(["src/", "tests/"]);
    const result = runHook(PATH_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, "src", "index.ts") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(0);
  });
});

// ════════════════════════════════════════════════════════
// Gate Bypass Detection (gate-guard.js)
// ════════════════════════════════════════════════════════
describe("Gate bypass detection", () => {
  it("blocks write to src/main.ts with PENDING gate", () => {
    setupDir();
    writeGates("PENDING");
    const result = runHook(GATE_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, "src", "main.ts") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(2);
  });

  it("allows write to .ai/state.yaml (exempt)", () => {
    setupDir();
    writeGates("PENDING");
    const result = runHook(GATE_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, ".ai", "state.yaml") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(0);
  });

  it("allows write to .ai/HANDOFF.md (exempt)", () => {
    setupDir();
    writeGates("PENDING");
    const result = runHook(GATE_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, ".ai", "HANDOFF.md") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(0);
  });

  it("allows any write when no .ai/ directory exists", () => {
    setupDir();
    rmSync(join(TEST_ROOT, ".ai"), { recursive: true });
    const result = runHook(GATE_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, "src", "main.ts") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(0);
  });

  it("allows any write when Loop not activated (no gates.yaml)", () => {
    setupDir();
    // .ai/ exists with state.yaml but no gates.yaml → Loop not active
    const result = runHook(GATE_GUARD, {
      tool_name: "Write",
      tool_input: { file_path: join(TEST_ROOT, "src", "main.ts") },
      cwd: TEST_ROOT,
    }, TEST_ROOT);
    expect(result.exitCode).toBe(0);
  });
});

// ════════════════════════════════════════════════════════
// SEC-004: Expanded Dangerous Command Detection
// ════════════════════════════════════════════════════════
describe("SEC-004: Expanded dangerous command detection", () => {
  const dangerousCommands = [
    { cmd: "dd if=/dev/zero of=/dev/sda", label: "dd disk write" },
    { cmd: "xcopy src dest /E /I", label: "xcopy" },
    { cmd: "robocopy src dest /MIR", label: "robocopy" },
    { cmd: "icacls C:\\secret /grant Everyone:F", label: "icacls" },
    { cmd: "takeown /f C:\\secret", label: "takeown" },
    { cmd: "reg add HKLM\\SOFTWARE\\test /v val /d 1", label: "reg add" },
    { cmd: "Rename-Item old.txt new.txt", label: "PowerShell Rename-Item" },
    { cmd: "Set-Acl -Path C:\\file -Acl $acl", label: "PowerShell Set-Acl" },
    { cmd: "Invoke-Expression 'Remove-Item C:\\file'", label: "PowerShell Invoke-Expression" },
    { cmd: "Set-Content -Path file.txt -Value 'data'", label: "PowerShell Set-Content" },
    { cmd: "Out-File -FilePath output.txt", label: "PowerShell Out-File" },
    { cmd: "Remove-Item file.txt", label: "PowerShell Remove-Item" },
  ];

  for (const { cmd, label } of dangerousCommands) {
    it(`detects dangerous: ${label}`, () => {
      setupDir();
      writeGates("PENDING");
      const result = runHook(GATE_GUARD, {
        tool_name: "Bash",
        tool_input: { command: cmd },
        cwd: TEST_ROOT,
      });
      expect(result.exitCode).toBe(2);
    });
  }
});
