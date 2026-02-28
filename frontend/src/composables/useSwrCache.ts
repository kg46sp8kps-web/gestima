/**
 * SWR (Stale-While-Revalidate) composable.
 *
 * Poskytuje:
 *  - `lastFetched` — timestamp posledního úspěšného fetch
 *  - `isRevalidating` — background refresh probíhá (UI: malý spinner)
 *  - `isStale(staleMs)` — zda jsou data starší než staleMs
 *  - `fetchIfStale(fetcher, staleMs)` — přeskočí fetch pokud data jsou fresh
 *  - `markFetched()` — nastavit timestamp po úspěšném ručním fetch
 */

import { ref, type Ref } from 'vue'

export interface SwrState {
  lastFetched: Ref<Date | null>
  isRevalidating: Ref<boolean>
  isStale: (staleMs: number) => boolean
  markFetched: () => void
}

export function useSwrCache(): SwrState {
  const lastFetched = ref<Date | null>(null)
  const isRevalidating = ref(false)

  function isStale(staleMs: number): boolean {
    if (!lastFetched.value) return true
    return Date.now() - lastFetched.value.getTime() > staleMs
  }

  function markFetched() {
    lastFetched.value = new Date()
  }

  return {
    lastFetched,
    isRevalidating,
    isStale,
    markFetched,
  }
}
