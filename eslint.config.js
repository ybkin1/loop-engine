// Better-Harness finding "no-self-enforcement-pipeline":
// 为治理框架自身的代码变更提供最小化 lint 门禁。
// 采用 ESLint v9 flat config + typescript-eslint（不启用类型感知规则，保持快速）。
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  {
    ignores: ["dist/**", "coverage/**", "node_modules/**", ".test-loop-tmp/**", "**/*.js", "**/*.cjs", "**/*.mjs"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.node,
      },
    },
    rules: {
      // 治理框架大量使用 any 作为 YAML/动态结构的边界，暂不强制。
      "@typescript-eslint/no-explicit-any": "off",
      // 允许未使用变量以下划线开头（约定俗成的忽略标记）。
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // require 语句在个别 CJS 脚本中出现，交由 typecheck/build 把关。
      "@typescript-eslint/no-require-imports": "off",
    },
  },
);
