export interface BatchSet {
  id: number
  set_number: string
  part_id: number | null
  name: string
  status: string  // 'draft' | 'frozen'
  frozen_at: string | null
  created_at: string
  version: number
  batch_count: number
}
