import { describe, test, expect } from "vitest";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// Better-Harness finding "skill-constraints-unenforced"：
// stable-guard.mjs 是 stable/ 保护约束的机械执行层，必须有回归测试守护。

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const GUARD_PATH = join(__dirname, "..", "scripts", "guards", "stable-guard.mjs");
const REPO_ROOT = join(__dirname, "..");

function runGuard(
  event: object | string,
  env: Record<string, string> = {},
): { exitCode: number; stderr: string; stdout: string } {
  const input = typeof event === "string" ? event : JSON.stringify(event);
  const result = spawnSync("node", [GUARD_PATH], {
    input,
    encoding: "utf-8",
    timeout: 5000,
    env: { ...process.env, ...env },
  });
  return {
    exitCode: result.status ?? -1,
    stderr: result.stderr ?? "",
    stdout: result.stdout ?? "",
  };
}

describe("stable-guard.mjs", () => {
  test("Write 到 stable/ → exit 2 阻断", () => {
    const result = runGuard({
      tool_name: "Write",
      tool_input: { file_path: join(REPO_ROOT, "stable", "current-loop-protocol.md") },
    });
    expect(result.exitCode).toBe(2);
    expect(result.stderr).toContain("stable");
  });

  test("Edit 到 stable/ 子路径 → exit 2 阻断", () => {
    const result = runGuard({
      tool_name: "Edit",
      tool_input: { file_path: join(REPO_ROOT, "stable", "user-origin.md") },
    });
    expect(result.exitCode).toBe(2);
  });

  test("Write 到 stable/ 之外 → exit 0 放行", () => {
    const result = runGuard({
      tool_name: "Write",
      tool_input: { file_path: join(REPO_ROOT, "src", "core", "state-machine.ts") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("Read 类工具 → exit 0 放行（即使目标是 stable/）", () => {
    const result = runGuard({
      tool_name: "Read",
      tool_input: { file_path: join(REPO_ROOT, "stable", "current-loop-protocol.md") },
    });
    expect(result.exitCode).toBe(0);
  });

  test("promotion gate 授权（LOOP_STABLE_PROMOTION=1）→ exit 0 放行", () => {
    const result = runGuard(
      {
        tool_name: "Write",
        tool_input: { file_path: join(REPO_ROOT, "stable", "current-loop-protocol.md") },
      },
      { LOOP_STABLE_PROMOTION: "1" },
    );
    expect(result.exitCode).toBe(0);
    expect(result.stderr).toContain("promotion gate");
  });

  test("畸形 JSON 输入 → exit 非 0（SEC-005 fail-close）", () => {
    const result = runGuard("{{{{INVALID_JSON");
    expect(result.exitCode).not.toBe(0);
  });

  test("缺少 file_path 的写操作 → exit 0（无目标可判断）", () => {
    const result = runGuard({ tool_name: "Write", tool_input: {} });
    expect(result.exitCode).toBe(0);
  });

  test("前缀相似路径（stable-x/）不被误伤 → exit 0", () => {
    const result = runGuard({
      tool_name: "Write",
      tool_input: { file_path: join(REPO_ROOT, "stable-archive", "doc.md") },
    });
    expect(result.exitCode).toBe(0);
  });
});
