import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // T-0014-B: 全局测试超时 15s（并行负载下偶发 5s 默认超时导致 flaky）
    testTimeout: 15_000,
    hookTimeout: 15_000,
    // Better-Harness finding "test-coverage-unquantified":
    // 量化测试覆盖深度，识别核心安全路径的分支盲区。
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      // 只统计 src 下的产品代码，排除测试、构建产物与类型声明。
      include: ["src/**/*.ts"],
      exclude: [
        "src/**/*.d.ts",
        "dist/**",
        "tests/**",
        "node_modules/**",
      ],
      // 全量阈值仅作基线提示，不阻断 CI（后续可按核心模块逐步收紧）。
      thresholds: {
        lines: 0,
        functions: 0,
        branches: 0,
        statements: 0,
      },
    },
  },
});
