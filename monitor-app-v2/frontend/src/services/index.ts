import { apiClient } from './api'
import type { LoginRequest, Token, Domain, LighthouseMetric } from '@/types'

export const authService = {
  login: async (credentials: LoginRequest): Promise<Token> => {
    const response = await apiClient.post('/auth/login', credentials)
    return response.data
  },

  register: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/register', { username, password })
    return response.data
  },

  logout: () => {
    localStorage.removeItem('access_token')
  },
}

export const domainService = {
  getAll: async () => {
    const response = await apiClient.get<Domain[]>('/domains/')
    return response.data
  },

  getById: async (id: number) => {
    const response = await apiClient.get<Domain>(`/domains/${id}`)
    return response.data
  },

  create: async (data: { url: string; name?: string; check_interval?: number }) => {
    const response = await apiClient.post('/domains/', data)
    return response.data
  },

  update: async (id: number, data: Partial<Domain>) => {
    const response = await apiClient.put(`/domains/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    await apiClient.delete(`/domains/${id}`)
  },

  getMetrics: async (domainId: number, limit: number = 10) => {
    const response = await apiClient.get<LighthouseMetric[]>(`/domains/${domainId}/metrics?limit=${limit}`)
    return response.data
  },

  triggerAudit: async (domainId: number) => {
    const response = await apiClient.post(`/domains/${domainId}/audit`)
    return response.data
  },
}

export const metricsService = {
  getAll: async (limit: number = 50) => {
    const response = await apiClient.get<LighthouseMetric[]>(`/metrics/?limit=${limit}`)
    return response.data
  },

  getAverage: async () => {
    const response = await apiClient.get('/metrics/average')
    return response.data
  },
}
