/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./frontend/index.html",
    "./frontend/src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: ['class'],
  theme: {
    extend: {
      // Map Tailwind colors to CSS variables (parametric design!)
      colors: {
        // Primary colors
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          light: 'var(--color-primary-light)',
          dark: 'var(--color-primary-dark)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          hover: 'var(--color-secondary-hover)',
        },
        danger: {
          DEFAULT: 'var(--color-danger)',
          hover: 'var(--color-danger-hover)',
          dark: 'var(--color-danger-dark)',
        },
        success: {
          DEFAULT: 'var(--color-success)',
          hover: 'var(--color-success-hover)',
          light: 'var(--color-success-light)',
          dark: 'var(--color-success-dark)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          hover: 'var(--color-warning-hover)',
          light: 'var(--color-warning-light)',
        },
        info: {
          DEFAULT: 'var(--color-info)',
          hover: 'var(--color-info-hover)',
        },

        // Backgrounds
        bg: {
          base: 'var(--bg-base)',
          surface: 'var(--bg-surface)',
          raised: 'var(--bg-raised)',
          input: 'var(--bg-input)',
          deepest: 'var(--bg-deepest)',
        },

        // Text colors
        text: {
          primary: 'var(--text-primary)',
          body: 'var(--text-body)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          disabled: 'var(--text-disabled)',
        },

        // Borders
        border: {
          DEFAULT: 'var(--border-default)',
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        },

        // States
        state: {
          hover: 'var(--state-hover)',
          active: 'var(--state-active)',
          selected: 'var(--state-selected)',
          'focus-bg': 'var(--state-focus-bg)',
          'focus-border': 'var(--state-focus-border)',
        },
      },

      // Border radius from design system
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
      },

      // Shadows from design system
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },

      // Font sizes from design system
      fontSize: {
        '2xs': 'var(--text-2xs)',
        xs: 'var(--text-xs)',
        sm: 'var(--text-sm)',
        base: 'var(--text-base)',
        lg: 'var(--text-lg)',
        xl: 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
        '4xl': 'var(--text-4xl)',
        '5xl': 'var(--text-5xl)',
        '6xl': 'var(--text-6xl)',
        '7xl': 'var(--text-7xl)',
        '8xl': 'var(--text-8xl)',
      },

      // Spacing from design system
      spacing: {
        1: 'var(--space-1)',
        2: 'var(--space-2)',
        3: 'var(--space-3)',
        4: 'var(--space-4)',
        5: 'var(--space-5)',
        6: 'var(--space-6)',
        8: 'var(--space-8)',
        10: 'var(--space-10)',
        12: 'var(--space-12)',
      },

      // Font families
      fontFamily: {
        sans: 'var(--font-sans)',
        mono: 'var(--font-mono)',
      },

      // Transitions
      transitionDuration: {
        fast: 'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
      },
    },
  },
  plugins: [],
}
