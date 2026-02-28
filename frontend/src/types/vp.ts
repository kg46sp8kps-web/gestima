export interface VpListItem {
  job: string
  suffix: string
  item: string | null
  description: string | null
  job_stat: string
  qty_released: number | null
  qty_complete: number | null
  qty_scrapped: number | null
  start_date: string | null
  end_date: string | null
  oper_count: number
}
