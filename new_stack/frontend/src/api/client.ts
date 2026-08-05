import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (email: string, password: string) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  
  register: (email: string, password: string) => {
    return api.post('/auth/register', { email, password })
  },
  
  getCurrentUser: () => {
    return api.get('/auth/me')
  },
}

export const domainsApi = {
  getDomains: () => {
    return api.get('/domains/')
  },
  
  createDomain: (data: { url: string; name?: string; check_interval_minutes?: number }) => {
    return api.post('/domains/', data)
  },
  
  getDomain: (id: number) => {
    return api.get(`/domains/${id}`)
  },
  
  updateDomain: (id: number, data: Partial<{ url: string; name: string; is_active: boolean; check_interval_minutes: number }>) => {
    return api.put(`/domains/${id}`, data)
  },
  
  deleteDomain: (id: number) => {
    return api.delete(`/domains/${id}`)
  },
  
  getMetrics: (id: number, limit: number = 50) => {
    return api.get(`/domains/${id}/metrics?limit=${limit}`)
  },
  
  triggerCheck: (id: number) => {
    return api.post(`/domains/${id}/check`)
  },
}

export const dashboardApi = {
  getSummary: () => {
    return api.get('/dashboard')
  },
  
  getAlerts: (limit: number = 50) => {
    return api.get(`/alerts?limit=${limit}`)
  },
}
