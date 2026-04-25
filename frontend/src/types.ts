export interface Overview {
  days_history: number
  unique_endpoints: number
  unique_fqdns: number
  total_events: number
  candidate_applications: number
  candidate_segments: number
  draft_illumio_objects: number
  high_confidence_recs: number
  time_saved_weeks: number
  earliest: string | null
  latest: string | null
  analyzed: boolean
}

export interface Dependency {
  id: number
  client_ip: string
  fqdn: string
  first_seen: string | null
  last_seen: string | null
  query_count: number
  days_observed: number
  confidence_score: number
  is_internal: boolean
  answer_ips_stable: boolean
}

export interface ClientProfile {
  client_ip: string
  first_seen: string | null
  last_seen: string | null
  total_queries: number
  unique_fqdns: number
  top_fqdns: string[]
  subnet: string | null
  owner: string | null
  site: string | null
  business_unit: string | null
  hostname: string | null
}

export interface Recommendation {
  id: number
  type: string
  name: string
  confidence: number
  evidence: Record<string, unknown>
  status: string
  illumio_payload: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface WorkloadDetailResponse {
  profile: ClientProfile | null
  dependencies: Dependency[]
  rcode_distribution: Record<string, number>
  timeline: Array<{ date: string; count: number }>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
