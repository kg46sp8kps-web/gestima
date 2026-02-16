/**
 * TimeVision Pinia Store
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DrawingFileInfo, TimeVisionEstimation, TimeVisionListItem } from '@/types/time-vision'
import type { ProcessingStep, CalibrationUpdate } from '@/api/time-vision'
import {
  fetchDrawings as apiFetchDrawings,
  processDrawingOpenAISSE,
  processDrawingFeaturesSSE,
  fetchEstimations as apiFetchEstimations,
  fetchOpenAIEstimation as apiFetchOpenAIEstimation,
  fetchFeaturesEstimation as apiFetchFeaturesEstimation,
  calibrateEstimation as apiCalibrateEstimation,
  deleteEstimation as apiDeleteEstimation,
  fetchModelInfo as apiFetchModelInfo,
  saveCorrectedFeatures as apiSaveCorrectedFeatures,
  fetchFeatureTypes as apiFetchFeatureTypes,
} from '@/api/time-vision'
import type { ModelInfo, FeatureTypesCatalog } from '@/api/time-vision'

export const useTimeVisionStore = defineStore('timeVision', () => {
  const drawings = ref<DrawingFileInfo[]>([])
  const estimations = ref<TimeVisionListItem[]>([])

  // Model info
  const modelInfo = ref<ModelInfo | null>(null)

  // Feature types catalog (loaded once, cached)
  const featureTypesCatalog = ref<FeatureTypesCatalog | null>(null)

  // OpenAI line (primary)
  const openaiEstimation = ref<TimeVisionEstimation | null>(null)
  const openaiProcessing = ref(false)
  const openaiProcessingStep = ref<ProcessingStep | null>(null)
  const openaiError = ref<string | null>(null)
  let abortOpenAIProcessing: (() => void) | null = null

  // Features line
  const featuresEstimation = ref<TimeVisionEstimation | null>(null)
  const featuresProcessing = ref(false)
  const featuresProcessingStep = ref<ProcessingStep | null>(null)
  const featuresError = ref<string | null>(null)
  let abortFeaturesProcessing: (() => void) | null = null

  async function loadDrawings() {
    try {
      openaiError.value = null
      drawings.value = await apiFetchDrawings()
    } catch (err: unknown) {
      openaiError.value = (err as Error).message
    }
  }

  async function loadEstimations(status?: string) {
    try {
      openaiError.value = null
      estimations.value = await apiFetchEstimations(status)
    } catch (err: unknown) {
      openaiError.value = (err as Error).message
    }
  }

  async function removeEstimation(id: number) {
    try {
      openaiError.value = null
      await apiDeleteEstimation(id)
      if (openaiEstimation.value?.id === id) {
        openaiEstimation.value = null
      }
      await loadEstimations()
    } catch (err: unknown) {
      openaiError.value = (err as Error).message
    }
  }

  async function calibrateOpenAI(id: number, data: CalibrationUpdate) {
    try {
      openaiError.value = null
      const result = await apiCalibrateEstimation(id, data)
      openaiEstimation.value = result
      await loadEstimations()
      await loadDrawings()
      return result
    } catch (err: unknown) {
      openaiError.value = (err as Error).message
      throw err
    }
  }

  // === Model info ===

  async function loadModelInfo() {
    try {
      modelInfo.value = await apiFetchModelInfo()
    } catch {
      // non-critical, ignore
    }
  }

  async function loadFeatureTypes() {
    if (featureTypesCatalog.value) return // already loaded
    try {
      featureTypesCatalog.value = await apiFetchFeatureTypes()
    } catch {
      // non-critical, ignore
    }
  }

  // === OpenAI line ===

  async function loadOpenAIEstimation(filename: string) {
    try {
      openaiError.value = null
      openaiEstimation.value = await apiFetchOpenAIEstimation(filename)
    } catch (err: unknown) {
      openaiError.value = (err as Error).message
    }
  }

  function processFileOpenAI(filename: string, fileId?: number | null, partId?: number | null): Promise<TimeVisionEstimation> {
    openaiProcessing.value = true
    openaiProcessingStep.value = null
    openaiError.value = null

    return new Promise((resolve, reject) => {
      abortOpenAIProcessing = processDrawingOpenAISSE(
        filename,
        (step) => {
          openaiProcessingStep.value = step
        },
        async (result) => {
          openaiEstimation.value = result
          openaiProcessing.value = false
          openaiProcessingStep.value = null
          await loadDrawings()
          resolve(result)
        },
        (errMsg) => {
          openaiError.value = errMsg
          openaiProcessing.value = false
          openaiProcessingStep.value = null
          reject(new Error(errMsg))
        },
        fileId,
        partId,
      )
    })
  }

  function cancelOpenAIProcessing() {
    if (abortOpenAIProcessing) {
      abortOpenAIProcessing()
      abortOpenAIProcessing = null
      openaiProcessing.value = false
      openaiProcessingStep.value = null
    }
  }

  // === Features line ===

  async function loadFeaturesEstimation(filename: string) {
    try {
      featuresError.value = null
      featuresEstimation.value = await apiFetchFeaturesEstimation(filename)
    } catch (err: unknown) {
      featuresError.value = (err as Error).message
    }
  }

  function processFeaturesOpenAI(filename: string, fileId?: number | null): Promise<TimeVisionEstimation> {
    featuresProcessing.value = true
    featuresProcessingStep.value = null
    featuresError.value = null

    return new Promise((resolve, reject) => {
      abortFeaturesProcessing = processDrawingFeaturesSSE(
        filename,
        (step) => {
          featuresProcessingStep.value = step
        },
        async (result) => {
          featuresEstimation.value = result
          featuresProcessing.value = false
          featuresProcessingStep.value = null
          await loadDrawings()
          resolve(result)
        },
        (errMsg) => {
          featuresError.value = errMsg
          featuresProcessing.value = false
          featuresProcessingStep.value = null
          reject(new Error(errMsg))
        },
        fileId,
      )
    })
  }

  function cancelFeaturesProcessing() {
    if (abortFeaturesProcessing) {
      abortFeaturesProcessing()
      abortFeaturesProcessing = null
      featuresProcessing.value = false
      featuresProcessingStep.value = null
    }
  }

  async function saveCorrectedFeatures(id: number, correctedJson: string, version: number) {
    try {
      featuresError.value = null
      const result = await apiSaveCorrectedFeatures(id, correctedJson, version)
      featuresEstimation.value = result
      await loadEstimations()
      await loadDrawings()
      return result
    } catch (err: unknown) {
      featuresError.value = (err as Error).message
      throw err
    }
  }

  return {
    drawings,
    estimations,
    loadDrawings,
    loadEstimations,
    removeEstimation,
    // Model info
    modelInfo,
    loadModelInfo,
    // Feature types catalog
    featureTypesCatalog,
    loadFeatureTypes,
    // OpenAI line (primary)
    openaiEstimation,
    openaiProcessing,
    openaiProcessingStep,
    openaiError,
    loadOpenAIEstimation,
    processFileOpenAI,
    cancelOpenAIProcessing,
    calibrateOpenAI,
    // Features line
    featuresEstimation,
    featuresProcessing,
    featuresProcessingStep,
    featuresError,
    loadFeaturesEstimation,
    processFeaturesOpenAI,
    cancelFeaturesProcessing,
    saveCorrectedFeatures,
  }
})
