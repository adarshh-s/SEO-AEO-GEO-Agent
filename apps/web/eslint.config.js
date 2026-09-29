import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

// RTL safety: physical-direction Tailwind utilities break mirroring in Arabic.
// Use logical ones instead: ms-/me-/ps-/pe-/start-/end-/text-start/border-s/rounded-s…
const PHYSICAL_CLASS =
  /(^|\s|:)-?(ml|mr|pl|pr|left|right|border-l|border-r|rounded-l|rounded-r|rounded-tl|rounded-tr|rounded-bl|rounded-br|text-left|text-right|float-left|float-right|scroll-ml|scroll-mr)(-|\s|$)/;
const rtlMessage =
  "Use logical Tailwind classes (ms-, me-, ps-, pe-, start-, end-, text-start, border-s, rounded-s…) so Arabic RTL mirrors correctly.";

export default tseslint.config(
  { ignores: ["dist", "src/lib/*.gen.ts", "playwright-report", "test-results"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: { ecmaVersion: 2022, globals: globals.browser },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "no-restricted-syntax": [
        "error",
        { selector: `JSXAttribute[name.name='className'] Literal[value=${PHYSICAL_CLASS}]`, message: rtlMessage },
        { selector: `JSXAttribute[name.name='className'] TemplateElement[value.raw=${PHYSICAL_CLASS}]`, message: rtlMessage },
        { selector: `CallExpression[callee.name=/^(cn|cva)$/] Literal[value=${PHYSICAL_CLASS}]`, message: rtlMessage },
      ],
    },
  },
);
