import { create } from 'zustand'
import api from '../api/client'

interface User {
  id: string
  email: string
  name: string | null
  role: 'admin' | 'lead' | 'manager'
  is_active: boolean
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isLoading: false,
  
  login: async (email: string, password: string) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      set({ token: data.access_token })
      await fetchUser()
    } finally {
      set({ isLoading: false })
    }
  },
  
  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
  },
  
  fetchUser: async () => {
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data })
    } catch {
      localStorage.removeItem('access_token')
      set({ user: null, token: null })
    }
  },
}))

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const fetchUser = useAuth((s) => s.fetchUser)
  const token = useAuth((s) => s.token)
  
  React.useEffect(() => {
    if (token) fetchUser()
  }, [token, fetchUser])
  
  return children
}
