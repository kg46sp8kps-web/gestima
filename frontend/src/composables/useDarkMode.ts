/**
 * Dark Mode Toggle
 * Persists preference in localStorage, applies CSS classes
 */

import { ref, watch, onMounted } from 'vue';
import type { ThemeMode } from '@/design/tokens';

const STORAGE_KEY = 'gestima_theme_mode';
const isDark = ref<boolean>(true); // Default: dark (existing style)

export function useDarkMode() {
  // Initialize from localStorage (FORCE dark mode only)
  onMounted(() => {
    // GESTIMA v1.7: Force dark mode (light mode not ready yet)
    // Clear any old light mode preference
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light') {
      localStorage.setItem(STORAGE_KEY, 'dark');
    }

    // Always dark mode for now
    isDark.value = true;
    applyTheme();
  });

  // Apply theme to DOM
  function applyTheme() {
    const root = document.documentElement;

    if (isDark.value) {
      root.classList.remove('light-mode');
      root.classList.add('dark-mode');
    } else {
      root.classList.remove('dark-mode');
      root.classList.add('light-mode');
    }
  }

  // Toggle theme
  function toggle() {
    isDark.value = !isDark.value;
  }

  // Set specific theme
  function setTheme(mode: ThemeMode) {
    isDark.value = mode === 'dark';
  }

  // Watch for changes and persist
  watch(isDark, (newValue) => {
    localStorage.setItem(STORAGE_KEY, newValue ? 'dark' : 'light');
    applyTheme();
  });

  return {
    isDark,
    toggle,
    setTheme
  };
}
