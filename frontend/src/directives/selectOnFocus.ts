import type { App, Directive } from 'vue'

const selectOnFocus: Directive<HTMLInputElement> = {
  mounted(el) {
    el.addEventListener('focus', () => el.select())
  },
}

export function registerDirectives(app: App) {
  app.directive('select-on-focus', selectOnFocus)
}
