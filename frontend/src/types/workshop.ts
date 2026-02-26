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
}

/** Dílnická transakce (lokální buffer) */
export interface WorkshopTransaction {
  id: number
  infor_job: string
  infor_suffix: string | null
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
  operNum: string | null
  mode: 'setup' | 'production' | null  // Mód zachycený při startu (pro správný stop TransType)
}
