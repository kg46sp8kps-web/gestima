/**
 * Debounce Composable
 * Returns a debounced ref that updates after delay
 */

import { ref, watch, type Ref } from 'vue'

export interface UseDebounceOptions {
  delay?: number
  immediate?: boolean
}

/**
 * Create a debounced ref from a source ref
 * @param source - Source ref to debounce
 * @param delay - Delay in ms (default 300)
 * @param options - Additional options
 */
export function useDebouncedRef<T>(
  source: Ref<T>,
  delay = 300,
  options: UseDebounceOptions = {}
): Ref<T> {
  const { immediate = false } = options

  const debounced = ref(source.value) as Ref<T>
  let timeout: ReturnType<typeof setTimeout> | null = null

  watch(source, (newValue) => {
    if (timeout) {
      clearTimeout(timeout)
    }

    if (immediate && debounced.value !== newValue) {
      debounced.value = newValue
    } else {
      timeout = setTimeout(() => {
        debounced.value = newValue
      }, delay)
    }
  })

  return debounced
}

/**
 * Create a debounced function
 * @param fn - Function to debounce
 * @param delay - Delay in ms (default 300)
 */
export function useDebounce<T extends (...args: any[]) => any>(
  fn: T,
  delay = 300
): {
  debouncedFn: (...args: Parameters<T>) => void
  cancel: () => void
  flush: () => void
} {
  let timeout: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<T> | null = null

  function debouncedFn(...args: Parameters<T>): void {
    lastArgs = args

    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      fn(...args)
      lastArgs = null
    }, delay)
  }

  function cancel(): void {
    if (timeout) {
      clearTimeout(timeout)
      timeout = null
    }
    lastArgs = null
  }

  function flush(): void {
    if (timeout && lastArgs) {
      clearTimeout(timeout)
      timeout = null
      fn(...lastArgs)
      lastArgs = null
    }
  }

  return { debouncedFn, cancel, flush }
}

/**
 * Watch a source with debouncing
 * @param source - Source to watch
 * @param callback - Callback to execute
 * @param delay - Delay in ms
 */
export function watchDebounced<T>(
  source: Ref<T>,
  callback: (value: T, oldValue: T) => void,
  delay = 300
): () => void {
  let timeout: ReturnType<typeof setTimeout> | null = null

  const stopWatch = watch(source, (newValue, oldValue) => {
    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      callback(newValue, oldValue)
    }, delay)
  })

  // Return cleanup function
  return () => {
    if (timeout) {
      clearTimeout(timeout)
    }
    stopWatch()
  }
}
