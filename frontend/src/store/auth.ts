import { create } from 'zustand'
import { useEffect } from 'react'
import api from '../api/client'
import { User } from '../types'

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
      localStorage.setItem('refresh_token', data.refresh_token)
      set({ token: data.access_token })
      await useAuth.getState().fetchUser()
    } finally {
      set({ isLoading: false })
    }
  },
  
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
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
  
  useEffect(() => {
    if (token) fetchUser()
  }, [token, fetchUser])
  
  return children
}
