export interface User {
  id: number
  email: string
  is_active: boolean
  created_at: string
}

export interface Domain {
  id: number
  url: string
  name: string | null
  owner_id: number
  is_active: boolean
  check_interval_minutes: number
  created_at: string
  updated_at: string | null
}

export interface LighthouseMetric {
  id: number
  domain_id: number
  performance_score: number | null
  accessibility_score: number | null
  best_practices_score: number | null
  seo_score: number | null
  pwa_score: number | null
  first_contentful_paint: number | null
  largest_contentful_paint: number | null
  total_blocking_time: number | null
  cumulative_layout_shift: number | null
  speed_index: number | null
  report_url: string | null
  checked_at: string
}

export interface Alert {
  id: number
  domain_id: number
  metric_name: string
  threshold_value: number
  current_value: number
  severity: 'info' | 'warning' | 'critical'
  message: string | null
  is_resolved: boolean
  created_at: string
  resolved_at: string | null
}

export interface DashboardSummary {
  total_domains: number
  active_domains: number
  total_checks: number
  alerts_count: number
  avg_performance_score: number | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
}
