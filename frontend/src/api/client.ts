import axios from 'axios'
import type {
  Overview,
  Dependency,
  ClientProfile,
  Recommendation,
  WorkloadDetailResponse,
  PaginatedResponse,
} from '../types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
})

export const getOverview = () => api.get<Overview>('/overview')

export const generateDemo = () =>
  api.post<{ status: string; message: string; events_inserted: number }>('/ingest/generate-demo')

export const runAnalysis = () =>
  api.post<{ status: string; correlation: unknown; enrichment: unknown; recommendations: unknown }>('/analyze')

export const getDependencies = (params?: Record<string, unknown>) =>
  api.get<PaginatedResponse<Dependency>>('/dependencies', { params })

export const getWorkloads = (params?: Record<string, unknown>) =>
  api.get<PaginatedResponse<ClientProfile>>('/workloads', { params })

export const getWorkloadDetail = (ip: string) =>
  api.get<WorkloadDetailResponse>(`/workloads/${encodeURIComponent(ip)}`)

export const getRecommendations = (params?: Record<string, unknown>) =>
  api.get<PaginatedResponse<Recommendation>>('/recommendations', { params })

export const updateRecommendation = (id: number, data: { status?: string; name?: string }) =>
  api.patch<Recommendation>(`/recommendations/${id}`, data)

export const pushToIllumio = (dryRun = true) =>
  api.post<{ dry_run: boolean; pushed: number; results: unknown[] }>(`/illumio/push?dry_run=${dryRun}`)
