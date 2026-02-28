/** Gestima Dílna — TypeScript typy pro dílnickou aplikaci */

// Field names potvrzeny z Infor REST API discovery (2026-02-26)
// SLJobRoutes: Job, Suffix, Type, Wc (ne WC!), OperNum, DerJobItem, JobDescription,
//              JobStat, JobQtyReleased, QtyComplete, QtyScrapped, JshSetupHrs, DerRunMchHrs,
//              SchedStartDate, SchedFinishDate
// IteCzTsdSLJobMatls: Material, Desc, TotCons, Qty, BatchCons

export type WorkshopTransType =
  | 'qty_complete'
  | 'scrap'
  | 'time'
  | 'start'
  | 'stop'
  | 'setup_start'  // Zahájit seřízení — odesílá se OKAMŽITĚ (@TTransType='1')
  | 'setup_end'    // Ukončit seřízení s hodinami (@TTransType='2')
export type WorkshopTxStatus = 'pending' | 'posting' | 'posted' | 'failed'

/** Fronta práce — flat položka operace z SLJobRoutes (job + op kontext, bez deduplikace) */
export interface WorkshopQueueItem {
  Job: string
  Suffix: string
  OperNum: string
  Wc: string
  State?: string | null
  StateAsd?: string | null
  DerJobItem: string | null
  JobDescription: string | null
  JobQtyReleased: number | null
  QtyComplete: number | null
  QtyScrapped: number | null
  JshSetupHrs: number | null
  DerRunMchHrs: number | null
  OpDatumSt: string | null   // Plánovaný začátek operace (z IteCzTsdJbrDetails)
  OpDatumSp: string | null   // Plánovaný konec operace (z IteCzTsdJbrDetails)
}

/** Zakázka/operace z Inforu (SLJobRoutes — deduplikováno Python-side) */
export interface WorkshopJob {
  Job: string
  Suffix: string
  Type: string
  Wc: string            // Pracoviště — lowercase c (ne WC!)
  OperNum: string
  DerJobItem: string    // Číslo dílu (ne Item)
  JobDescription: string | null  // Popis (ne ItemDescription)
  JobStat: string       // R=Released, F=Firm, C=Closed (ne Status)
  JobQtyReleased: number | null  // Vydané množství (ne Qty)
  QtyComplete: number | null
  QtyScrapped: number | null
  JshSetupHrs: number | null
  DerRunMchHrs: number | null
  // SchedStartDate/SchedFinishDate nejsou na IteCzSLJobRoutes IDO
}

/** Operace zakázky z Inforu (SLJobRoutes per-job, remapováno) */
export interface WorkshopOperation {
  Job: string
  Suffix: string
  OperNum: string
  Wc: string            // Pracoviště — lowercase c (ne WC!)
  QtyReleased: number | null
  QtyComplete: number | null
  ScrapQty: number | null
  SetupHrs: number | null   // Plánované hodiny seřízení
  RunHrs: number | null     // Plánované hodiny výroby (na kus)
  OpDatumSt: string | null  // Plánovaný začátek operace (z IteCzTsdJbrDetails)
  OpDatumSp: string | null  // Plánovaný konec operace (z IteCzTsdJbrDetails)
}

/** Materiál k operaci zakázky (IteCzTsdSLJobMatls) */
export interface WorkshopMaterial {
  Material: string      // Kód položky
  Desc: string | null   // Popis
  TotCons: number | null  // Celková spotřeba
  Qty: number | null    // Množství na kus
  BatchCons: number | null  // Spotřeba pro dávku
  QtyIssued?: number | null // Již odvedeno
  RemainingCons?: number | null // Zbývá odvést
  UM?: string | null    // Jednotka (např. kg, m, ks)
  UMs?: string[]        // Dostupné jednotky materiálu
  QtyByUM?: Record<string, number> // Množství na ks podle jednotky
  BatchConsByUM?: Record<string, number> // Dávková spotřeba podle jednotky
}

export type WorkshopOrderOperationStatus = 'done' | 'in_progress' | 'idle'

export interface WorkshopOrderOperationCell {
  oper_num: string
  wc: string
  status: WorkshopOrderOperationStatus | string
  state_text: string | null
}

export interface WorkshopOrderMaterialCell {
  material: string
  status: 'done' | 'idle'
}

export interface WorkshopOrderVpCandidate {
  job: string
  suffix: string
  job_stat: string | null
  qty_released: number | null
  qty_complete: number | null
  qty_scrapped: number | null
  item: string | null
  customer_name: string | null
  due_date: string | null
  operations: WorkshopOrderOperationCell[]
}

export interface WorkshopOrderOverviewRow {
  row_id: string
  customer_code: string | null
  customer_name: string | null
  delivery_code: string | null
  delivery_name: string | null
  co_num: string
  co_line: string
  co_release: string
  item: string | null
  description: string | null
  material_ready: boolean
  qty_ordered: number | null
  qty_shipped: number | null
  qty_on_hand: number | null
  qty_available: number | null
  qty_wip: number | null
  due_date: string | null
  promise_date: string | null
  confirm_date: string | null
  vp_candidates: WorkshopOrderVpCandidate[]
  selected_vp_job: string | null
  operations: WorkshopOrderOperationCell[]
  materials: WorkshopOrderMaterialCell[]
  record_date: string | null
}

/** Plán stroje — operace s JobStat rozlišením (R/F/S/W) + CO deadline + priorita */
export interface MachinePlanItem extends WorkshopQueueItem {
  JobStat: string  // R=Released, F=Firm, S=Scheduled, W=Waiting
  OrderDueDate?: string | null  // Termín zakázky (Item-based matching z CO)
  CoNum?: string | null         // Číslo zakázky
  IsHot?: boolean               // Urgentní VP (z production_priorities)
  Priority?: number             // Priorita (5=hot, 20=urgent, 100=normal)
  Tier?: 'hot' | 'urgent' | 'normal'  // Odvozený tier
  IsPositioned?: boolean        // true = ručně pozicovaný v DnD (má DB pozici)
}

export type WorkshopSortDir = 'asc' | 'desc'
export type WorkshopQueueSortBy =
  | 'OpDatumSt'
  | 'OpDatumSp'
  | 'Job'
  | 'OperNum'
  | 'Wc'
  | 'DerJobItem'
  | 'JobDescription'
  | 'QtyComplete'
  | 'JobQtyReleased'
export type WorkshopOperationSortBy =
  | 'OpDatumSt'
  | 'OpDatumSp'
  | 'OperNum'
  | 'Wc'
  | 'QtyReleased'
  | 'QtyComplete'
  | 'ScrapQty'
export type WorkshopMaterialSortBy = 'Material' | 'Desc' | 'TotCons' | 'Qty' | 'BatchCons'

export interface WorkshopMaterialIssueCreate {
  job: string
  suffix?: string
  oper_num: string
  material: string
  um?: string | null
  qty: number
  wc?: string | null
  location?: string | null
  lot?: string | null
}

export interface WorkshopMaterialIssueResult {
  Job: string
  Suffix: string
  OperNum: string
  Material: string
  QtyIssued: number
  UM?: string | null
  Wc: string | null
  Whse?: string | null
  Location: string | null
  Lot: string | null
  Infor: Record<string, unknown>
}

/** Dílnická transakce (lokální buffer) */
export interface WorkshopTransaction {
  id: number
  infor_job: string
  infor_suffix: string | null
  infor_item: string | null
  oper_num: string
  wc: string | null
  trans_type: WorkshopTransType
  qty_completed: number | null
  qty_scrapped: number | null
  qty_moved: number | null
  scrap_reason: string | null
  actual_hours: number | null
  oper_complete: boolean
  job_complete: boolean
  started_at: string | null
  finished_at: string | null
  status: WorkshopTxStatus
  error_msg: string | null
  posted_at: string | null
  created_by: string | null
  created_at: string
  updated_at: string
  version: number
}

/** Data pro vytvoření transakce */
export interface WorkshopTransactionCreate {
  infor_job: string
  infor_suffix: string
  infor_item?: string | null
  oper_num: string
  wc?: string | null
  trans_type: WorkshopTransType
  qty_completed?: number | null
  qty_scrapped?: number | null
  qty_moved?: number | null
  scrap_reason?: string | null
  actual_hours?: number | null
  oper_complete?: boolean
  job_complete?: boolean
  started_at?: string | null
  finished_at?: string | null
}

/** Stav časovače */
export interface WorkshopTimer {
  running: boolean
  startedAt: Date | null
  job: string | null
  suffix: string | null
  operNum: string | null
  inforItem: string | null
  wc: string | null
  mode: 'setup' | 'production' | null  // Mód zachycený při startu (pro správný stop TransType)
}
