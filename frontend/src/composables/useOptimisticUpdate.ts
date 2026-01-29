/**
 * Optimistic Updates Pattern
 * UI updates instantly, API in background, rollback on error
 * = No blink, no lag, smooth UX!
 */

import { type Ref } from 'vue';

interface OptimisticOptions {
  onSuccess?: (result: any) => void;
  onError?: (error: any) => void;
  showToast?: boolean;
}

export function useOptimisticUpdate<T extends { id: number | string }>() {
  /**
   * Optimistic DELETE
   * UI removes item instantly, API call in background
   */
  async function optimisticDelete(
    items: Ref<T[]>,
    id: T['id'],
    deleteFn: (id: T['id']) => Promise<void>,
    options: OptimisticOptions = {}
  ): Promise<void> {
    // 1. Backup current state
    const backup = [...items.value];
    const index = items.value.findIndex(item => item.id === id);

    if (index === -1) {
      throw new Error(`Item with id ${id} not found`);
    }

    // 2. Optimistic UI update (INSTANT!)
    items.value = items.value.filter(item => item.id !== id);

    try {
      // 3. Background API call
      await deleteFn(id);

      // 4. Success callback
      options.onSuccess?.('Item deleted successfully');
    } catch (error) {
      // 5. Rollback on error
      items.value = backup;

      // 6. Error callback
      options.onError?.(error);
      throw error;
    }
  }

  /**
   * Optimistic UPDATE
   * UI shows changes instantly, API call in background
   */
  async function optimisticUpdate(
    items: Ref<T[]>,
    id: T['id'],
    updates: Partial<T>,
    updateFn: (id: T['id'], data: Partial<T>) => Promise<T>,
    options: OptimisticOptions = {}
  ): Promise<T> {
    // 1. Backup
    const backup = [...items.value];
    const index = items.value.findIndex(item => item.id === id);

    if (index === -1) {
      throw new Error(`Item with id ${id} not found`);
    }

    // 2. Optimistic UI (INSTANT!)
    items.value[index] = { ...items.value[index], ...updates } as T;

    try {
      // 3. Background API call
      const result = await updateFn(id, updates);

      // 4. Replace with server response (may include computed fields)
      items.value[index] = result;

      // 5. Success callback
      options.onSuccess?.(result);
      return result;
    } catch (error) {
      // 6. Rollback on error
      items.value = backup;

      // 7. Error callback
      options.onError?.(error);
      throw error;
    }
  }

  /**
   * Optimistic CREATE
   * UI shows new item instantly (with temp ID), API call in background
   */
  async function optimisticCreate(
    items: Ref<T[]>,
    tempItem: T,
    createFn: (data: Omit<T, 'id'>) => Promise<T>,
    options: OptimisticOptions = {}
  ): Promise<T> {
    // 1. Backup
    const backup = [...items.value];

    // 2. Optimistic UI (add temp item INSTANTLY!)
    items.value = [...items.value, tempItem];

    try {
      // 3. Background API call
      const result = await createFn(tempItem as Omit<T, 'id'>);

      // 4. Replace temp item with real one (real ID from server)
      const tempIndex = items.value.findIndex(item => item.id === tempItem.id);
      if (tempIndex !== -1) {
        items.value[tempIndex] = result;
      }

      // 5. Success callback
      options.onSuccess?.(result);
      return result;
    } catch (error) {
      // 6. Rollback on error (remove temp item)
      items.value = backup;

      // 7. Error callback
      options.onError?.(error);
      throw error;
    }
  }

  /**
   * Optimistic REORDER
   * UI reorders instantly, API call in background
   */
  async function optimisticReorder(
    items: Ref<T[]>,
    fromIndex: number,
    toIndex: number,
    reorderFn: (items: T[]) => Promise<void>,
    options: OptimisticOptions = {}
  ): Promise<void> {
    // 1. Backup
    const backup = [...items.value];

    // 2. Optimistic UI (reorder INSTANTLY!)
    const newItems = [...items.value];
    const [movedItem] = newItems.splice(fromIndex, 1);
    if (movedItem) {
      newItems.splice(toIndex, 0, movedItem);
    }
    items.value = newItems;

    try {
      // 3. Background API call
      await reorderFn(newItems);

      // 4. Success callback
      options.onSuccess?.('Reordered successfully');
    } catch (error) {
      // 5. Rollback on error
      items.value = backup;

      // 6. Error callback
      options.onError?.(error);
      throw error;
    }
  }

  return {
    optimisticDelete,
    optimisticUpdate,
    optimisticCreate,
    optimisticReorder
  };
}
