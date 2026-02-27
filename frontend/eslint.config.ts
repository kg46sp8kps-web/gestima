import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginPlaywright from 'eslint-plugin-playwright'
import pluginVitest from '@vitest/eslint-plugin'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

// To allow more languages other than `ts` in `.vue` files, uncomment the following lines:
// import { configureVueProject } from '@vue/eslint-config-typescript'
// configureVueProject({ scriptLangs: ['ts', 'tsx'] })
// More info at https://github.com/vuejs/eslint-config-typescript/#advanced-setup

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,ts,mts,tsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  ...pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

  {
    ...pluginPlaywright.configs['flat/recommended'],
    files: ['e2e/**/*.{test,spec}.{js,ts,jsx,tsx}'],
  },

  // Legacy E2E suite uses conditional flows and explicit waits.
  // Keep signal clean for application lint while we migrate tests incrementally.
  {
    name: 'app/e2e-transitional-rules',
    files: ['e2e/**/*.{test,spec}.{js,ts,jsx,tsx}'],
    rules: {
      'playwright/no-wait-for-timeout': 'off',
      'playwright/no-wait-for-selector': 'off',
      'playwright/no-conditional-in-test': 'off',
      'playwright/no-conditional-expect': 'off',
      'playwright/expect-expect': 'off',
      'playwright/no-force-option': 'off',
    },
  },

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },

  ...pluginOxlint.configs['flat/recommended'],

  {
    name: 'app/no-direct-axios-in-ui',
    files: ['src/components/**/*.{vue,ts}', 'src/stores/**/*.ts'],
    rules: {
      'no-restricted-imports': ['error', {
        paths: [{
          name: 'axios',
          message: 'Use shared API modules in src/api instead of direct axios in components/stores.'
        }]
      }]
    }
  },

  // Atomic UI components intentionally use single-word names (Button, Input, Modal, etc.)
  {
    name: 'app/ui-component-names',
    files: ['src/components/ui/*.vue'],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },

  // Block raw HTML form elements — use UI components instead
  {
    name: 'app/use-ui-components',
    files: ['src/components/**/*.vue', 'src/views/**/*.vue'],
    ignores: ['src/components/ui/**', 'src/views/auth/**'],
    rules: {
      'vue/no-restricted-html-elements': ['error',
        {
          element: 'input',
          message: 'Use <Input>, <Input bare>, <InlineInput>, or <DragDropZone>. For file inputs add <!-- intentional: programmatic trigger -->.',
        },
        {
          element: 'select',
          message: 'Use <InlineSelect>, <TypeAheadSelect>, or <CuttingModeButtons>.',
        },
        {
          element: 'textarea',
          message: 'Use <Textarea> from components/ui/.',
        },
      ],
    },
  },

  skipFormatting,
)
