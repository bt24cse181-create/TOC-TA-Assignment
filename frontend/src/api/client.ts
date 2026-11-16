import axios, { AxiosError } from 'axios';
import type {
  WorkflowListItem,
  WorkflowResponse,
  CaseResponse,
  EventSubmissionResponse,
  HealthResponse,
  PaginatedAnomalyResponse,
  BatchSimulationResponse,
  SimulationCaseInput,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Error helper ─────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number | null;
  detail: string;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = message;
  }
}

function handleError(err: unknown): never {
  if (err instanceof AxiosError) {
    const status = err.response?.status ?? null;
    const detail =
      err.response?.data?.detail ??
      err.response?.data?.message ??
      err.message ??
      'Unknown API error';
    throw new ApiError(String(detail), status);
  }
  throw new ApiError(String(err));
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  try {
    const { data } = await api.get<HealthResponse>('/api/v1/health');
    return data;
  } catch (err) {
    return handleError(err);
  }
}

// ─── Workflows ────────────────────────────────────────────────────────────────

export async function getWorkflows(): Promise<WorkflowListItem[]> {
  try {
    const { data } = await api.get<WorkflowListItem[]>('/api/v1/workflows');
    return data;
  } catch (err) {
    return handleError(err);
  }
}

export async function getWorkflow(
  identifier: string | number
): Promise<WorkflowResponse> {
  try {
    const { data } = await api.get<WorkflowResponse>(
      `/api/v1/workflows/${identifier}`
    );
    return data;
  } catch (err) {
    return handleError(err);
  }
}

// ─── Cases ────────────────────────────────────────────────────────────────────

export async function createCase(params: {
  workflow_code: string;
  case_id?: string;
  total_amount?: number;
  user_id?: string;
  metadata_json?: Record<string, unknown>;
}): Promise<CaseResponse> {
  try {
    const { data } = await api.post<CaseResponse>('/api/v1/cases', params);
    return data;
  } catch (err) {
    return handleError(err);
  }
}

export async function getCase(caseId: string): Promise<CaseResponse> {
  try {
    const { data } = await api.get<CaseResponse>(`/api/v1/cases/${caseId}`);
    return data;
  } catch (err) {
    return handleError(err);
  }
}

// ─── Events ───────────────────────────────────────────────────────────────────

export async function submitEvent(
  caseId: string,
  params: {
    event_name: string;
    execution_duration_ms?: number;
    payload_json?: Record<string, unknown>;
    idempotency_key?: string;
  }
): Promise<EventSubmissionResponse> {
  try {
    const { data } = await api.post<EventSubmissionResponse>(
      `/api/v1/cases/${caseId}/events`,
      params
    );
    return data;
  } catch (err) {
    return handleError(err);
  }
}

// ─── Anomalies ────────────────────────────────────────────────────────────────

export async function getAnomalies(params?: {
  page?: number;
  page_size?: number;
  case_id?: string;
  severity?: string;
  detector_type?: string;
}): Promise<PaginatedAnomalyResponse> {
  try {
    const { data } = await api.get<PaginatedAnomalyResponse>(
      '/api/v1/anomalies',
      { params }
    );
    return data;
  } catch (err) {
    return handleError(err);
  }
}

export async function getCaseAnomalies(
  caseId: string
): Promise<import('../types').AnomalyResultResponse[]> {
  try {
    const { data } = await api.get(`/api/v1/cases/${caseId}/anomalies`);
    return data;
  } catch (err) {
    return handleError(err);
  }
}

// ─── Batch Simulation ─────────────────────────────────────────────────────────

export async function runBatchSimulation(params: {
  workflow_code: string;
  cases: SimulationCaseInput[];
  persist_results?: boolean;
}): Promise<BatchSimulationResponse> {
  try {
    const { data } = await api.post<BatchSimulationResponse>(
      '/api/v1/simulation/run-batch',
      params
    );
    return data;
  } catch (err) {
    return handleError(err);
  }
}
