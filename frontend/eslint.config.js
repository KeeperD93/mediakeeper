/**
 * ESLint 9 flat config — MediaKeeper frontend.
 *
 * Enforces the public coding conventions documented in CONTRIBUTING.md.
 * In particular:
 *   - No literal style="..." attributes in templates (zero inline-style rule).
 *   - No window.confirm(), no alert() — use useConfirm() + showToast().
 *   - No inline <svg>, use lucide-vue-next.
 *   - No direct fetch() in components (must go through useApi).
 */

import js from '@eslint/js'
import globals from 'globals'
import vue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import prettierConfig from 'eslint-config-prettier'

export default [
  // Ignore build output and vendor directories.
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'coverage/**',
      'public/**',
      'scripts/**', // custom build helpers, inspected manually
    ],
  },

  // Base JS recommendations.
  js.configs.recommended,

  // Vue recommended (flat).
  ...vue.configs['flat/recommended'],

  // Project-wide settings and house rules.
  {
    files: ['**/*.{js,mjs,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parser: vueParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: false },
      },
      globals: {
        ...globals.browser,
        ...globals.es2024,
        // Vue 3 macros auto-imported by @vitejs/plugin-vue.
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        defineOptions: 'readonly',
        defineSlots: 'readonly',
        defineModel: 'readonly',
        withDefaults: 'readonly',
      },
    },
    rules: {
      // --- House rules ---------------------------------------------------

      // No literal style="..." on template elements.
      // Dynamic :style bindings are allowed (handled separately below).
      'vue/html-self-closing': 'off', // keep existing style, not a debt
      'vue/no-static-inline-styles': [
        'error',
        { allowBinding: true },
      ],

      // No native confirm / alert. Use useConfirm() and showToast().
      'no-restricted-globals': [
        'error',
        { name: 'confirm', message: 'Use useConfirm() from @/composables/useConfirm.' },
        { name: 'alert',   message: 'Use showToast() from useToast.' },
      ],
      'no-alert': 'error',

      // Components must not call fetch() directly. Go through useApi.
      // Allowed in useApi itself and in the App-shell health polling.
      'no-restricted-syntax': [
        'warn',
        {
          selector: "CallExpression[callee.name='fetch']",
          message: 'Use apiGet/apiPost/apiPut/apiDelete from useApi.',
        },
      ],

      // Prevent literal <svg> in templates (ask for lucide-vue-next).
      // Enforced at review time rather than by ESLint (too many false positives
      // for decorative inline SVG in isolated icon wrappers). Kept as a note.

      // Hygiene.
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
      'no-debugger': 'error',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': ['error', { allowEmptyCatch: true }], // documented exception: catch blocks may be intentionally empty
      'prefer-const': 'warn',
      'no-var': 'error',

      // Vue specifics — tuned to the project.
      'vue/multi-word-component-names': 'off', // App.vue, HomeFab.vue, etc.
      'vue/no-v-html': 'warn', // occasional controlled usage (i18n-rendered markup)
      'vue/require-default-prop': 'off',
      'vue/require-prop-types': 'warn',
      'vue/attribute-hyphenation': ['warn', 'always'],
      'vue/v-on-event-hyphenation': ['warn', 'always'],
      'vue/singleline-html-element-content-newline': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-indent': ['warn', 2, { alignAttributesVertically: false }],
    },
  },

  // Loosen rules for the scripts/ helpers (Node scripts, not browser code).
  {
    files: ['scripts/**/*.{js,mjs}'],
    languageOptions: {
      globals: { ...globals.node },
    },
    rules: {
      'no-console': 'off',
    },
  },

  // useApi is the single place allowed to call fetch() (it wraps it).
  {
    files: ['src/composables/useApi.js'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },

  // App.vue owns the backend health polling — fetch() allowed there.
  {
    files: ['src/App.vue'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },

  // NotifTemplatesTab.vue intentionally mutates sub-fields of the `webhooks`
  // Array prop. The parent does not reassign the array; this is a two-way
  // binding shortcut that would otherwise require a full refactor of every
  // editable sub-field.
  {
    files: ['src/components/notifications/NotifTemplatesTab.vue'],
    rules: {
      'vue/no-mutating-props': 'off',
    },
  },

  // Prettier compatibility layer (disables conflicting stylistic rules).
  prettierConfig,
]
