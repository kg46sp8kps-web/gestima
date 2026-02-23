import type { Batch } from './batch'

export interface BatchSet {
  id: number
  set_number: string
  part_id: number | null
  name: string
  status: string // 'draft' | 'frozen'
  frozen_at: string | null
  created_at: string
  version: number
  batch_count: number
}

export interface BatchSetWithBatches {
  id: number
  set_number: string
  part_id: number | null
  name: string
  status: string // 'draft' | 'frozen'
  frozen_at: string | null
  frozen_by_id: number | null
  created_at: string
  updated_at: string | null
  version: number
  batches: Batch[]
  batch_count: number
  total_value: number
}

export interface BatchSetUpdate {
  name: string
  version: number
}
