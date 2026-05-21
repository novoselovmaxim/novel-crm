export interface Company {
  id: string
  name: string
  inn: string
  ogrn?: string | null
  kpp?: string | null
  region: string | null
  address?: string | null
  phone: string | null
  email: string | null
  website: string | null
  director?: string | null
  activity_main: string | null
  activity_code?: string | null
  revenue: number | null
  employees?: number | null
  call_status: string
  call_count: number
  comment_static: string | null
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
