/**
 * TimeVision API client
 */

import { apiClient } from '@/api/client'
import type {
  DrawingFileInfo,
  TimeVisionEstimation,
  TimeVisionListItem,
} from '@/types/time-vision'

export interface ProcessingStep {
  step: number
  total: number
  label: string
}

export async function fetchDrawings(): Promise<DrawingFileInfo[]> {
  const { data } = await apiClient.get<DrawingFileInfo[]>('/time-vision/drawings')
  return data
}

export function getDrawingPdfUrl(filename: string, _fileId?: number | null): string {
  // ADR-044: Always use filename-based endpoint for PDF preview.
  // pdf.js (pdfjsLib.getDocument) makes XHR requests WITHOUT Authorization headers,
  // so /api/files/{id}/download (which requires auth) would return 401.
  // The /api/time-vision/drawings/{filename}/pdf endpoint has no auth requirement.
  // file_id is used only in process/SSE endpoints where fetch() sends explicit auth.
  return `/api/time-vision/drawings/${encodeURIComponent(filename)}/pdf`
}

export async function fetchEstimations(status?: string): Promise<TimeVisionListItem[]> {
  const params = status ? { status } : {}
  const { data } = await apiClient.get<TimeVisionListItem[]>('/time-vision/estimations', { params })
  return data
}

export interface CalibrationUpdate {
  complexity?: 'simple' | 'medium' | 'complex'
  part_type?: 'ROT' | 'PRI' | 'COMBINED'
  human_estimate_min?: number
  actual_time_min?: number
  actual_notes?: string | null
  version: number
}

export async function calibrateEstimation(
  id: number,
  data: CalibrationUpdate,
): Promise<TimeVisionEstimation> {
  const { data: result } = await apiClient.put<TimeVisionEstimation>(
    `/time-vision/estimations/${id}/calibrate`,
    data,
  )
  return result
}

export async function fetchEstimationById(id: number): Promise<TimeVisionEstimation> {
  const { data } = await apiClient.get<TimeVisionEstimation>(`/time-vision/estimations/${id}`)
  return data
}

export async function deleteEstimation(id: number): Promise<void> {
  await apiClient.delete(`/time-vision/estimations/${id}`)
}

/**
 * Process a drawing via OpenAI SSE - streams progress then final result.
 */
export function processDrawingOpenAISSE(
  filename: string,
  onStep: (step: ProcessingStep) => void,
  onResult: (estimation: TimeVisionEstimation) => void,
  onError: (error: string) => void,
  fileId?: number | null,
  partId?: number | null,
): () => void {
  const url = `/api/time-vision/process-openai`
  const token = localStorage.getItem('gestima_token')

  const controller = new AbortController()

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ filename, file_id: fileId ?? undefined, part_id: partId ?? undefined }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        onError(`HTTP ${response.status}: ${text}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError('No response body')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim()
            if (!data) continue
            try {
              const parsed = JSON.parse(data)
              if (currentEvent === 'step') {
                onStep(parsed as ProcessingStep)
              } else if (currentEvent === 'result') {
                onResult(parsed as TimeVisionEstimation)
              } else if (currentEvent === 'error') {
                onError(parsed.detail ?? 'Unknown error')
              }
            } catch {
              // skip unparseable lines
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message ?? 'Network error')
      }
    })

  return () => controller.abort()
}

export async function fetchOpenAIEstimation(filename: string, partId?: number | null): Promise<TimeVisionEstimation | null> {
  // ADR-045: Prefer part_id lookup (direct FK), fallback to filename
  if (partId) {
    const { data } = await apiClient.get<TimeVisionListItem[]>(
      `/time-vision/estimations/by-part/${partId}`,
      { params: { estimation_type: 'time_v1' } },
    )
    if (data.length > 0) {
      const first = data[0]!
      const { data: full } = await apiClient.get<TimeVisionEstimation>(`/time-vision/estimations/${first.id}`)
      return full
    }
    return null
  }

  // Legacy filename-based lookup
  const { data } = await apiClient.get<TimeVisionListItem[]>('/time-vision/estimations', {
    params: { estimation_type: 'time_v1', filename },
  })
  const match = data
    .filter((e) => e.pdf_filename === filename)
    .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
  if (match.length === 0) return null
  const first = match[0]!
  const { data: full } = await apiClient.get<TimeVisionEstimation>(`/time-vision/estimations/${first.id}`)
  return full
}

export interface ModelInfo {
  model: string
  is_fine_tuned: boolean
  provider: string
}

export async function fetchModelInfo(): Promise<ModelInfo> {
  const { data } = await apiClient.get<ModelInfo>('/time-vision/model-info')
  return data
}

export function exportTrainingDataUrl(): string {
  return '/api/time-vision/export-training'
}

export function processDrawingFeaturesSSE(
  filename: string,
  onStep: (step: ProcessingStep) => void,
  onResult: (result: TimeVisionEstimation) => void,
  onError: (error: string) => void,
  fileId?: number | null,
  partId?: number | null,
): () => void {
  const url = `/api/time-vision/process-features`
  const token = localStorage.getItem('gestima_token')

  const controller = new AbortController()

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ filename, file_id: fileId ?? undefined, part_id: partId ?? undefined }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        onError(`HTTP ${response.status}: ${text}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError('No response body')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim()
            if (!data) continue
            try {
              const parsed = JSON.parse(data)
              if (currentEvent === 'step') {
                onStep(parsed as ProcessingStep)
              } else if (currentEvent === 'result') {
                onResult(parsed as TimeVisionEstimation)
              } else if (currentEvent === 'error') {
                onError(parsed.detail ?? 'Unknown error')
              }
            } catch {
              // skip unparseable lines
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message ?? 'Network error')
      }
    })

  return () => controller.abort()
}

export async function fetchFeaturesEstimation(filename: string): Promise<TimeVisionEstimation | null> {
  const { data } = await apiClient.get<TimeVisionListItem[]>('/time-vision/estimations', {
    params: { estimation_type: 'features_v2', filename },
  })
  if (data.length === 0) return null
  const first = data[0]!
  const { data: full } = await apiClient.get<TimeVisionEstimation>(`/time-vision/estimations/${first.id}`)
  return full
}

export async function saveCorrectedFeatures(
  estimationId: number,
  correctedJson: string,
  version: number,
): Promise<TimeVisionEstimation> {
  const { data } = await apiClient.put<TimeVisionEstimation>(
    `/time-vision/estimations/${estimationId}/features`,
    { features_corrected_json: correctedJson, version },
  )
  return data
}

export interface FeaturesTimeCalculation {
  calculated_time_min: number
  feature_times: Array<{ type: string; detail: string; count: number; time_sec: number; method?: string }>
}

export async function calculateFeaturesTime(
  estimationId: number,
  cuttingMode: 'low' | 'mid' | 'high',
): Promise<FeaturesTimeCalculation> {
  const { data } = await apiClient.post<FeaturesTimeCalculation>(
    `/time-vision/estimations/${estimationId}/calculate-time`,
    { cutting_mode: cuttingMode },
  )
  return data
}

export interface FeatureTypeMeta {
  key: string
  label_cs: string
  description: string
  example: string
  group: string
  has_time: boolean
}

export interface FeatureTypesCatalog {
  types: FeatureTypeMeta[]
  groups: Record<string, string>
}

export async function fetchFeatureTypes(): Promise<FeatureTypesCatalog> {
  const { data } = await apiClient.get<FeatureTypesCatalog>('/time-vision/feature-types')
  return data
}

export function exportFeaturesTrainingDataUrl(): string {
  return '/api/time-vision/export-features-training'
}
