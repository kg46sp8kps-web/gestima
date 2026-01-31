/**
 * Partner types - Customers and Suppliers
 */

export type PartnerType = 'customer' | 'supplier' | 'both'

export interface Partner {
  id: number
  partner_number: string
  company_name: string
  ico?: string
  dic?: string
  email?: string
  phone?: string
  contact_person?: string
  street?: string
  city?: string
  postal_code?: string
  country: string
  is_customer: boolean
  is_supplier: boolean
  notes?: string
  version: number
  created_at: string
  updated_at: string
}

export interface PartnerCreate {
  company_name: string
  ico?: string
  dic?: string
  email?: string
  phone?: string
  contact_person?: string
  street?: string
  city?: string
  postal_code?: string
  country?: string
  is_customer: boolean
  is_supplier: boolean
  notes?: string
}

export interface PartnerUpdate {
  company_name?: string
  ico?: string
  dic?: string
  email?: string
  phone?: string
  contact_person?: string
  street?: string
  city?: string
  postal_code?: string
  country?: string
  is_customer?: boolean
  is_supplier?: boolean
  notes?: string
  version: number
}

export interface PartnersSearchResponse {
  partners: Partner[]
  total: number
}
