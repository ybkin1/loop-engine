import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // T-0014-B: 全局测试超时 15s（并行负载下偶发 5s 默认超时导致 flaky）
    testTimeout: 15_000,
    hookTimeout: 15_000,
  },
});
