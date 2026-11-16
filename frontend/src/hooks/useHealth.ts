import { useState, useEffect, useCallback, useRef } from 'react';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types';

export type ConnectionStatus = 'connected' | 'disconnected' | 'checking';

interface UseHealthReturn {
  health: HealthResponse | null;
  status: ConnectionStatus;
  error: string | null;
  refresh: () => void;
}

export function useHealth(pollIntervalMs = 15000): UseHealthReturn {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('checking');
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus('checking');
      const data = await getHealth();
      setHealth(data);
      setStatus('connected');
      setError(null);
    } catch (err) {
      setHealth(null);
      setStatus('disconnected');
      setError(err instanceof Error ? err.message : 'Connection failed');
    }
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, pollIntervalMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh, pollIntervalMs]);

  return { health, status, error, refresh };
}
