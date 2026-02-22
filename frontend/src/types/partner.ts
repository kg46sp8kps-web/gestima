export interface Partner {
  id: number
  partner_number: string
  company_name: string
  ico: string | null
  dic: string | null
  email: string | null
  phone: string | null
  contact_person: string | null
  street: string | null
  city: string | null
  postal_code: string | null
  country: string
  is_customer: boolean
  is_supplier: boolean
  notes: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface PartnerSearchResponse {
  partners: Partner[]
  total: number
  skip: number
  limit: number
}
