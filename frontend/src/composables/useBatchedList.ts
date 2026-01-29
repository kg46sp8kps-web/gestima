/**
 * Batched List Loading
 * Load items in chunks (100 items/batch) = <50ms per load
 * Prevents network bottleneck + smooth scrolling
 */

import { ref, shallowRef, readonly, type Ref } from 'vue';

export interface BatchedListOptions<T> {
  fetchFn: (skip: number, limit: number) => Promise<T[]>;
  batchSize?: number;
  prefetchThreshold?: number; // % scrolled before prefetch next batch
  cacheKey?: string; // For shared caching between components
}

export interface BatchedListReturn<T> {
  items: Readonly<Ref<T[]>>;
  loading: Readonly<Ref<boolean>>;
  hasMore: Readonly<Ref<boolean>>;
  currentBatch: Readonly<Ref<number>>;
  loadBatch: (batchIndex: number) => Promise<void>;
  loadNext: () => Promise<void>;
  reset: () => void;
  onScroll: (scrollTop: number, containerHeight: number, contentHeight: number) => void;
}

/**
 * Global cache for batched data (shared between components/panels)
 * Key = cacheKey + batchIndex
 */
const globalBatchCache = new Map<string, any[]>();

export function useBatchedList<T>(options: BatchedListOptions<T>): BatchedListReturn<T> {
  const {
    fetchFn,
    batchSize = 100,
    prefetchThreshold = 0.8, // Load next when 80% scrolled
    cacheKey
  } = options;

  // State (shallowRef for performance!)
  const items = shallowRef<T[]>([]);
  const loading = ref(false);
  const hasMore = ref(true);
  const currentBatch = ref(0);

  // Loaded batches tracking (prevent duplicate fetches)
  const loadedBatches = new Set<number>();

  // Pending request (prevent concurrent fetches of same batch)
  let pendingRequest: Promise<void> | null = null;

  /**
   * Load specific batch
   */
  async function loadBatch(batchIndex: number): Promise<void> {
    // Already loaded?
    if (loadedBatches.has(batchIndex)) {
      return;
    }

    // Already loading this batch?
    if (loading.value && pendingRequest) {
      return pendingRequest;
    }

    // Check global cache first (if cacheKey provided)
    if (cacheKey) {
      const cacheKeyFull = `${cacheKey}_${batchIndex}`;
      const cached = globalBatchCache.get(cacheKeyFull);
      if (cached) {
        items.value = [...items.value, ...cached];
        loadedBatches.add(batchIndex);
        currentBatch.value = batchIndex;
        return;
      }
    }

    loading.value = true;

    pendingRequest = (async () => {
      try {
        const skip = batchIndex * batchSize;
        const newItems = await fetchFn(skip, batchSize);

        // Mark batch as loaded
        loadedBatches.add(batchIndex);

        // Cache globally (if cacheKey provided)
        if (cacheKey) {
          const cacheKeyFull = `${cacheKey}_${batchIndex}`;
          globalBatchCache.set(cacheKeyFull, newItems);
        }

        // Append to items (shallowRef = fast!)
        items.value = [...items.value, ...newItems];

        // No more data?
        if (newItems.length < batchSize) {
          hasMore.value = false;
        }

        currentBatch.value = batchIndex;
      } catch (error) {
        console.error(`Failed to load batch ${batchIndex}:`, error);
        throw error;
      } finally {
        loading.value = false;
        pendingRequest = null;
      }
    })();

    return pendingRequest;
  }

  /**
   * Load next batch (scroll trigger)
   */
  async function loadNext(): Promise<void> {
    if (!hasMore.value || loading.value) return;

    await loadBatch(currentBatch.value + 1);
  }

  /**
   * Reset (for search/filter changes)
   */
  function reset(): void {
    items.value = [];
    loadedBatches.clear();
    currentBatch.value = 0;
    hasMore.value = true;
    loading.value = false;
    pendingRequest = null;

    // Clear global cache for this key
    if (cacheKey) {
      for (const key of globalBatchCache.keys()) {
        if (key.startsWith(`${cacheKey}_`)) {
          globalBatchCache.delete(key);
        }
      }
    }
  }

  /**
   * Scroll handler (auto-load next batch)
   * Call from component with scroll event data
   */
  function onScroll(scrollTop: number, containerHeight: number, contentHeight: number): void {
    if (!hasMore.value || loading.value) return;

    const scrollPercentage = (scrollTop + containerHeight) / contentHeight;

    // Trigger prefetch when threshold reached
    if (scrollPercentage > prefetchThreshold) {
      loadNext();
    }
  }

  return {
    items: items as Readonly<Ref<T[]>>,
    loading: loading as Readonly<Ref<boolean>>,
    hasMore: hasMore as Readonly<Ref<boolean>>,
    currentBatch: currentBatch as Readonly<Ref<number>>,
    loadBatch,
    loadNext,
    reset,
    onScroll
  };
}

/**
 * Clear all global cache (call on logout/session end)
 */
export function clearBatchCache(): void {
  globalBatchCache.clear();
}
