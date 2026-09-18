export interface VedDeclaration {
  id: string
  source_file: string
  direction: string
  inn: string | null
  company_name: string | null
  country_from: string | null
  country_to: string | null
  hs_code: string | null
  customs_value: number | null
  invoice_value: number | null
  stat_value: number | null
  net_weight: number | null
  gross_weight: number | null
  incoterms: string | null
  declaration_date: string | null
  row_data: Record<string, any>
  created_at: string | null
}

export interface VedProfile {
  id: string
  inn: string
  company_name: string | null
  directions: string[] | null
  total_declarations: number
  total_customs_value: number | null
  total_stat_value: number | null
  total_net_weight: number | null
  destination_countries: string[] | null
  source_countries: string[] | null
  hs_codes: string[] | null
  source_files: string[] | null
  contact_phone: string | null
  contact_email: string | null
  website: string | null
  director: string | null
  address: string | null
  region: string | null
  revenue: number | null
  employees: number | null
  ogrn: string | null
  activity: string | null
  company_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface VedProfileDetail extends VedProfile {
  declarations: VedDeclaration[]
}

export interface VedStats {
  total_profiles: number
  total_declarations: number
  with_company: number
  without_company: number
  import_count: number
  export_count: number
  total_customs_value: number | null
  top_countries: { country: string; count: number }[]
  top_hs_codes: { code: string; count: number }[]
}

export interface VedProfilesResponse {
  items: VedProfile[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
