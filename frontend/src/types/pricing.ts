export interface PriceBreakdown {
  // Stroje
  machine_amortization: number
  machine_labor: number
  machine_tools: number
  machine_overhead: number
  machine_total: number
  machine_setup_time_min: number
  machine_setup_cost: number
  machine_operation_time_min: number
  machine_operation_cost: number

  // Režie + Marže
  overhead_coefficient: number
  work_with_overhead: number
  overhead_markup: number
  overhead_percent: number
  margin_coefficient: number
  work_with_margin: number
  margin_markup: number
  margin_percent: number

  // Kooperace
  coop_cost_raw: number
  coop_coefficient: number
  coop_cost: number

  // Materiál
  material_cost_raw: number
  stock_coefficient: number
  material_cost: number

  // Celkem
  total_cost: number
  quantity: number
  cost_per_piece: number
  scrap_rate_percent: number
}
