import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, domainsApi, dashboardApi } from '../api/client'
import type { LoginCredentials, RegisterData } from '@/types'

export function useLogin() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ email, password }: LoginCredentials) => 
      authApi.login(email, password),
    onSuccess: (data) => {
      localStorage.setItem('token', data.data.access_token)
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: ({ email, password }: RegisterData) => 
      authApi.register(email, password),
  })
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['user'],
    queryFn: () => authApi.getCurrentUser(),
    enabled: !!localStorage.getItem('token'),
    retry: false,
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  
  return () => {
    localStorage.removeItem('token')
    queryClient.clear()
    window.location.href = '/login'
  }
}
