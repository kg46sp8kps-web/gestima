import type { App, Directive } from 'vue'

interface HandlerSet {
  mousedown: (e: MouseEvent) => void
  focus: () => void
  blur: () => void
}

const handlers = new WeakMap<HTMLInputElement, HandlerSet>()

const selectOnFocus: Directive<HTMLInputElement> = {
  mounted(el) {
    let isFocused = false
    let fromMouse = false

    const mousedownHandler = (e: MouseEvent) => {
      fromMouse = true
      if (!isFocused) {
        // První klik: zablokuj výchozí cursor positioning → žádné probliknutí
        e.preventDefault()
        el.focus()
        el.select()
      }
      // Druhý klik: nechej browser normálně pozicovat kurzor
    }

    const focusHandler = () => {
      if (!fromMouse) {
        // Tab nebo programatický focus — vyber okamžitě
        el.select()
      }
      isFocused = true
      fromMouse = false
    }

    const blurHandler = () => {
      isFocused = false
      fromMouse = false
    }

    handlers.set(el, { mousedown: mousedownHandler, focus: focusHandler, blur: blurHandler })
    el.addEventListener('mousedown', mousedownHandler)
    el.addEventListener('focus', focusHandler)
    el.addEventListener('blur', blurHandler)
  },
  beforeUnmount(el) {
    const hs = handlers.get(el)
    if (hs) {
      el.removeEventListener('mousedown', hs.mousedown)
      el.removeEventListener('focus', hs.focus)
      el.removeEventListener('blur', hs.blur)
      handlers.delete(el)
    }
  },
}

export function registerDirectives(app: App) {
  app.directive('select-on-focus', selectOnFocus)
}
