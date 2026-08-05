export interface User {
  id: number
  username: string
  is_active: boolean
  is_admin: boolean
  created_at: string
}

export interface Domain {
  id: number
  url: string
  name: string | null
  owner_id: number
  is_active: boolean
  check_interval: number
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
  time_to_interactive: number | null
  total_blocking_time: number | null
  cumulative_layout_shift: number | null
  report_url: string | null
  checked_at: string
}

export interface Alert {
  id: number
  domain_id: number
  alert_type: string
  threshold: number
  current_value: number
  message: string
  is_read: boolean
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface Token {
  access_token: string
  token_type: string
}
