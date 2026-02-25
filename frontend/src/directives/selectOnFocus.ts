import type { App, Directive } from 'vue'

const handlers = new WeakMap<HTMLInputElement, () => void>()

const selectOnFocus: Directive<HTMLInputElement> = {
  mounted(el) {
    const handler = () => el.select()
    handlers.set(el, handler)
    el.addEventListener('focus', handler)
  },
  beforeUnmount(el) {
    const handler = handlers.get(el)
    if (handler) {
      el.removeEventListener('focus', handler)
      handlers.delete(el)
    }
  },
}

export function registerDirectives(app: App) {
  app.directive('select-on-focus', selectOnFocus)
}
