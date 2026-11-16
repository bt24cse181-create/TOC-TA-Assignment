import { useState, useCallback } from 'react';
import { createCase, submitEvent, getCase } from '../api/client';
import type {
  CaseResponse,
  EventSubmissionResponse,
  HybridEvaluation,
} from '../types';

export interface ScenarioStep {
  event_name: string;
  duration_ms: number;
}

export interface ScenarioConfig {
  workflowCode: string;
  amount: number;
  userId: string;
  events: ScenarioStep[];
}

interface UseCaseReturn {
  activeCase: CaseResponse | null;
  lastEvaluation: HybridEvaluation | null;
  lastEventResponse: EventSubmissionResponse | null;
  eventHistory: EventSubmissionResponse[];
  loading: boolean;
  error: string | null;
  startNewCase: (
    workflowCode: string,
    amount?: number,
    userId?: string
  ) => Promise<CaseResponse | null>;
  sendEvent: (
    eventName: string,
    durationMs?: number
  ) => Promise<EventSubmissionResponse | null>;
  runScenario: (config: ScenarioConfig) => Promise<void>;
  refreshCase: () => Promise<void>;
  clearCase: () => void;
}

export function useCase(): UseCaseReturn {
  const [activeCase, setActiveCase] = useState<CaseResponse | null>(null);
  const [lastEvaluation, setLastEvaluation] =
    useState<HybridEvaluation | null>(null);
  const [lastEventResponse, setLastEventResponse] =
    useState<EventSubmissionResponse | null>(null);
  const [eventHistory, setEventHistory] = useState<EventSubmissionResponse[]>(
    []
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startNewCase = useCallback(
    async (
      workflowCode: string,
      amount?: number,
      userId?: string
    ): Promise<CaseResponse | null> => {
      try {
        setLoading(true);
        setError(null);
        setLastEvaluation(null);
        setLastEventResponse(null);
        setEventHistory([]);
        const data = await createCase({
          workflow_code: workflowCode,
          total_amount: amount,
          user_id: userId,
        });
        setActiveCase(data);
        return data;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create case');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const sendEvent = useCallback(
    async (
      eventName: string,
      durationMs?: number
    ): Promise<EventSubmissionResponse | null> => {
      if (!activeCase) {
        setError('No active case. Create a case first.');
        return null;
      }
      try {
        setLoading(true);
        setError(null);
        const resp = await submitEvent(activeCase.case_id, {
          event_name: eventName,
          execution_duration_ms: durationMs ?? 1200,
        });
        setLastEventResponse(resp);
        setLastEvaluation(resp.evaluation);
        setEventHistory((prev) => [...prev, resp]);
        // Update active case snapshot
        const refreshed = await getCase(activeCase.case_id);
        setActiveCase(refreshed);
        return resp;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send event');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [activeCase]
  );

  // Dedicated Scenario Runner that reliably chains new case creation and event execution
  const runScenario = useCallback(async (config: ScenarioConfig) => {
    try {
      setLoading(true);
      setError(null);
      setLastEvaluation(null);
      setLastEventResponse(null);
      setEventHistory([]);

      // 1. Create a fresh case instance
      const freshCase = await createCase({
        workflow_code: config.workflowCode,
        total_amount: config.amount,
        user_id: config.userId,
      });
      setActiveCase(freshCase);

      const historyAccumulator: EventSubmissionResponse[] = [];

      // 2. Execute steps sequentially
      for (let i = 0; i < config.events.length; i++) {
        const step = config.events[i];

        if (i > 0) {
          // Pause briefly between steps so user sees the automaton transition
          await new Promise((resolve) => setTimeout(resolve, 500));
        }

        const resp = await submitEvent(freshCase.case_id, {
          event_name: step.event_name,
          execution_duration_ms: step.duration_ms,
        });

        historyAccumulator.push(resp);
        setLastEventResponse(resp);
        setLastEvaluation(resp.evaluation);
        setEventHistory([...historyAccumulator]);

        const currentSnapshot = await getCase(freshCase.case_id);
        setActiveCase(currentSnapshot);

        // If the DFA failed, stop sequence so trap state is preserved
        if (!resp.evaluation.dfa.is_valid) {
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scenario execution failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshCase = useCallback(async () => {
    if (!activeCase) return;
    try {
      setLoading(true);
      const data = await getCase(activeCase.case_id);
      setActiveCase(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh case');
    } finally {
      setLoading(false);
    }
  }, [activeCase]);

  const clearCase = useCallback(() => {
    setActiveCase(null);
    setLastEvaluation(null);
    setLastEventResponse(null);
    setEventHistory([]);
    setError(null);
  }, []);

  return {
    activeCase,
    lastEvaluation,
    lastEventResponse,
    eventHistory,
    loading,
    error,
    startNewCase,
    sendEvent,
    runScenario,
    refreshCase,
    clearCase,
  };
}
