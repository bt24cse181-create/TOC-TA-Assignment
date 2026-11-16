// ─── Workflow Types ───────────────────────────────────────────────────────────

export interface WorkflowListItem {
  id: number;
  code: string;
  name: string;
  description: string | null;
  version: string;
  is_active: boolean;
  created_at: string;
  state_count: number;
  transition_count: number;
}

export type StateType =
  | 'START'
  | 'INTERMEDIATE'
  | 'TERMINAL_SUCCESS'
  | 'TERMINAL_FAILURE'
  | 'ERROR';

export interface WorkflowStateResponse {
  id: number;
  state_key: string;
  state_name: string;
  state_type: StateType;
  is_initial: boolean;
  is_terminal: boolean;
  max_retries?: number | null;
  description: string | null;
}

export interface WorkflowTransitionResponse {
  id: number;
  from_state_id: number;
  to_state_id: number;
  event_name: string;
  is_allowed: boolean;
  max_retries: number;
  condition_meta?: Record<string, unknown> | null;
  from_state_key?: string;
  to_state_key?: string;
  is_retry_transition?: boolean;
  description?: string | null;
}

export interface WorkflowResponse {
  id: number;
  code: string;
  name: string;
  description: string | null;
  version: string;
  is_active: boolean;
  created_at: string;
  states: WorkflowStateResponse[];
  transitions: WorkflowTransitionResponse[];
}

// ─── Case Types ───────────────────────────────────────────────────────────────

export type CaseStatus = 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ANOMALOUS';
export type AnomalySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type DetectorType = 'DFA' | 'ISOLATION_FOREST' | 'HYBRID';
export type AnomalyClassification =
  | 'NORMAL'
  | 'SYNTACTIC_ANOMALY'
  | 'BEHAVIORAL_ANOMALY'
  | 'COMPOUND_ANOMALY';

export interface EventLogResponse {
  id: number;
  case_id: string;
  event_name: string;
  sequence_number: number;
  from_state_key: string | null;
  to_state_key: string | null;
  is_valid_transition: boolean;
  execution_duration_ms: number | null;
  payload_json: Record<string, unknown> | null;
  occurred_at: string;
}

export interface DfaResult {
  is_valid: boolean;
  error_type: string | null;
  invalid_event: string | null;
  invalid_index: number | null;
  state_before_violation: string | null;
  message: string | null;
}

export interface MlResult {
  is_anomaly: boolean;
  score: number;
  threshold: number;
  top_contributing_features: [string, number][];
}

export interface HybridEvaluation {
  classification: AnomalyClassification;
  is_anomaly: boolean;
  severity: AnomalySeverity;
  explanation: string;
  is_completed: boolean;
  is_partial: boolean;
  final_state: string;
  visited_states: string[];
  dfa: DfaResult;
  ml: MlResult;
  metadata: {
    workflow_code: string;
    model_version: string;
  };
}

export interface AnomalyResultResponse {
  id: number;
  case_id: string;
  event_log_id?: number | null;
  detector_type: DetectorType;
  is_anomaly?: boolean;
  anomaly_score: number | null;
  anomaly_reason?: string;
  severity: AnomalySeverity;
  rule_violation?: string | null;
  detected_at: string;
  details_json?: Record<string, any> | null;
  classification?: AnomalyClassification;
  threshold_used?: number | null;
  explanation?: string | null;
  dfa_details?: DfaResult | null;
  ml_details?: MlResult | null;
}

export interface CaseResponse {
  id: number;
  case_id: string;
  workflow_id: number;
  current_state_key: string;
  status: CaseStatus;
  total_amount: number | null;
  user_id: string | null;
  retry_count: number;
  started_at: string;
  completed_at: string | null;
  metadata_json: Record<string, unknown> | null;
  events: EventLogResponse[];
  anomalies: AnomalyResultResponse[];
}

export interface EventSubmissionResponse {
  case_id: string;
  current_state: string;
  status: CaseStatus;
  event: EventLogResponse;
  evaluation: HybridEvaluation;
}

// ─── Health Types ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  database: {
    status: string;
    target: string;
  };
  ml_engine: {
    status: string;
    threshold: number;
  };
}

// ─── Anomaly List Types ───────────────────────────────────────────────────────

export interface PaginatedAnomalyResponse {
  items: AnomalyResultResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ─── Simulation Types ─────────────────────────────────────────────────────────

export interface SimulationCaseInput {
  events: { event_name: string; execution_duration_ms?: number }[];
  total_amount?: number;
  user_id?: string;
}

export interface BatchSimulationResponse {
  total_cases: number;
  anomaly_count: number;
  normal_count: number;
  results: Array<{
    case_id: string;
    classification: AnomalyClassification;
    severity: AnomalySeverity;
    is_anomaly: boolean;
    explanation: string;
  }>;
}

// ─── UI State Types ───────────────────────────────────────────────────────────

export type ActiveTab = 'simulator' | 'anomalies' | 'batch';
