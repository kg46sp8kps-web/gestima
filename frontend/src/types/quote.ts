export interface QuoteListItem {
  id: number
  quote_number: string
  partner_id: number | null
  title: string
  status: 'DRAFT' | 'SENT' | 'APPROVED' | 'REJECTED'
  total: number
  offer_deadline: string | null
  valid_until: string | null
  created_at: string
  version: number
}
