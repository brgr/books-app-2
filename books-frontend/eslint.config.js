import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import prettier from "eslint-config-prettier/flat";
import vue from "eslint-plugin-vue";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  globalIgnores(["dist/**", "dev-dist/**", "coverage/**", "test-results/**"]),
  {
    files: ["**/*.{js,mjs,cjs,ts,tsx,vue}"],
    extends: [js.configs.recommended, tseslint.configs.recommended, vue.configs["flat/recommended"]],
    languageOptions: {
      parserOptions: { parser: tseslint.parser },
    },
  },
  {
    files: ["src/**/*.{ts,tsx,vue}"],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ["*.{js,ts}", "src/**/*.test.ts"],
    languageOptions: { globals: globals.node },
  },
  prettier,
  {
    rules: {
      // Require braces
      curly: ["error", "all"],
    },
  },
);
