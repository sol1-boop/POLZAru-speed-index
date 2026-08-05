import { create } from 'zustand'
import { authService } from '@/services'
import type { Token } from '@/types'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  login: (credentials: { username: string; password: string }) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (credentials) => {
    const data: Token = await authService.login(credentials)
    localStorage.setItem('access_token', data.access_token)
    set({ token: data.access_token, isAuthenticated: true })
  },

  logout: () => {
    authService.logout()
    set({ token: null, isAuthenticated: false })
  },
}))
