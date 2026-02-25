export interface QuoteListItem {
  id: number
  quote_number: string
  partner_id: number | null
  title: string
  status: 'draft' | 'sent' | 'approved' | 'rejected'
  total: number
  offer_deadline: string | null
  valid_until: string | null
  created_at: string
  version: number
}

export interface QuoteItem {
  id: number
  quote_id: number
  part_id: number | null
  part_number: string | null
  part_name: string | null
  drawing_number: string | null
  quantity: number
  unit_price: number
  line_total: number
  batch_approx: boolean
  notes: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface QuoteDetail {
  id: number
  quote_number: string
  partner_id: number | null
  title: string
  description: string | null
  customer_request_number: string | null
  request_date: string | null
  offer_deadline: string | null
  valid_until: string | null
  delivery_terms: string | null
  status: 'draft' | 'sent' | 'approved' | 'rejected'
  sent_at: string | null
  approved_at: string | null
  rejected_at: string | null
  subtotal: number
  discount_percent: number
  discount_amount: number
  tax_percent: number
  tax_amount: number
  total: number
  notes: string | null
  items: QuoteItem[]
  version: number
  created_at: string
  updated_at: string
}
