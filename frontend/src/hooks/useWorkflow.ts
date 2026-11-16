import { useState, useEffect, useCallback } from 'react';
import { getWorkflows, getWorkflow } from '../api/client';
import type { WorkflowListItem, WorkflowResponse } from '../types';

function enrichWorkflow(wf: WorkflowResponse): WorkflowResponse {
  const stateMap = new Map(wf.states.map((s) => [s.id, s]));
  return {
    ...wf,
    transitions: wf.transitions.map((t) => {
      const from = stateMap.get(t.from_state_id);
      const to = stateMap.get(t.to_state_id);
      const isRetry =
        t.max_retries > 0 ||
        t.event_name.includes('RETRY') ||
        Boolean(t.condition_meta && Object.keys(t.condition_meta).length > 0);
      return {
        ...t,
        from_state_key: from?.state_key ?? '',
        to_state_key: to?.state_key ?? '',
        is_retry_transition: isRetry,
      };
    }),
  };
}

interface UseWorkflowReturn {
  workflows: WorkflowListItem[];
  selectedWorkflow: WorkflowResponse | null;
  loading: boolean;
  error: string | null;
  selectWorkflow: (codeOrId: string | number) => Promise<void>;
  refresh: () => void;
}

export function useWorkflow(): UseWorkflowReturn {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] =
    useState<WorkflowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadWorkflows = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getWorkflows();
      setWorkflows(data);
      // Auto-select first workflow
      if (data.length > 0 && !selectedWorkflow) {
        const full = await getWorkflow(data[0].code);
        setSelectedWorkflow(enrichWorkflow(full));
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflows');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectWorkflow = useCallback(async (codeOrId: string | number) => {
    try {
      setLoading(true);
      const full = await getWorkflow(codeOrId);
      setSelectedWorkflow(enrichWorkflow(full));
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load workflow'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  return {
    workflows,
    selectedWorkflow,
    loading,
    error,
    selectWorkflow,
    refresh: loadWorkflows,
  };
}
