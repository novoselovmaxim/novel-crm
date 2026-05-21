export interface Company {
  id: string
  name: string
  inn: string
  ogrn?: string | null
  kpp?: string | null
  org_form?: string | null
  reg_date?: string | null
  region: string | null
  address?: string | null
  tax_office?: string | null
  phone: string | null
  email: string | null
  website: string | null
  linkedin?: string | null
  director?: string | null
  director_title?: string | null
  director_inn?: string | null
  fin_director?: string | null
  contact_person?: string | null
  citizenship?: string | null
  activity_main: string | null
  activity_code?: string | null
  activity_other?: string | null
  niche?: string | null
  supply_subject?: string | null
  revenue: number | null
  profit?: number | null
  employees?: number | null
  capital?: number | null
  import_turnover?: string | null
  export_turnover?: string | null
  import_confirmed?: string | null
  foreign_payments?: string | null
  arbitrage?: string | null
  licenses?: string | null
  registries?: string | null
  msp?: string | null
  size?: string | null
  segment?: string | null
  priority?: string | null
  focus_link?: string | null
  source_orig?: string | null
  branches?: string | null
  comment_static: string | null
  call_status: string
  call_count: number
  next_call_date: string | null
  assigned_to: string | null
  last_called_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface User {
  id: string
  email: string
  name: string | null
  role: 'admin' | 'lead' | 'manager'
  is_active: boolean
  created_at: string
  tg_chat_id?: number | null
  tg_username?: string | null
}

export interface DashboardStats {
  total_companies: number
  new_companies: number
  in_progress: number
  interested: number
  meetings_scheduled: number
  refused: number
  calls_today: number
  tasks_today: number
  overdue: number
}

export interface CallLog {
  id: string
  company_id: string
  user_id: string
  call_status: string
  notes: string | null
  called_at: string
}
