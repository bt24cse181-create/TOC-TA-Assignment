import React, { useState, useEffect, useCallback } from 'react';
import { Shield, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { getAnomalies } from '../../api/client';
import type { PaginatedAnomalyResponse, AnomalyResultResponse } from '../../types';
import { ClassificationBadge } from '../Simulator/EventSimulator';

export const AnomalyHistory: React.FC = () => {
  const [data, setData] = useState<PaginatedAnomalyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [severityFilter, setSeverityFilter] = useState('');
  const [detectorFilter, setDetectorFilter] = useState('');
  const pageSize = 15;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await getAnomalies({
        page,
        page_size: pageSize,
        severity: severityFilter || undefined,
        detector_type: detectorFilter || undefined,
      });
      setData(resp);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load anomalies');
    } finally {
      setLoading(false);
    }
  }, [page, severityFilter, detectorFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-3">
      {/* Header & Filters */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5">
          <Shield size={15} className="text-blue-400" />
          Anomaly Log
          {data && (
            <span className="text-slate-500 font-normal text-xs">
              ({data.total} total)
            </span>
          )}
        </h2>
        <button
          onClick={load}
          className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="flex items-center gap-2">
        <Filter size={11} className="text-slate-500" />
        <select
          value={severityFilter}
          onChange={(e) => {
            setSeverityFilter(e.target.value);
            setPage(1);
          }}
          className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1 focus:outline-none"
        >
          <option value="">All Severities</option>
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <select
          value={detectorFilter}
          onChange={(e) => {
            setDetectorFilter(e.target.value);
            setPage(1);
          }}
          className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1 focus:outline-none"
        >
          <option value="">All Detectors</option>
          <option value="DFA">DFA</option>
          <option value="ISOLATION_FOREST">Isolation Forest</option>
          <option value="HYBRID">Hybrid</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <p className="text-[11px] text-red-400">{error}</p>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="text-center py-8 text-sm text-slate-500">Loading…</div>
      ) : data && data.items.length > 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="text-left px-3 py-2 font-medium">Case ID</th>
                <th className="text-left px-3 py-2 font-medium">Classification</th>
                <th className="text-left px-3 py-2 font-medium">Severity</th>
                <th className="text-left px-3 py-2 font-medium">Detector</th>
                <th className="text-left px-3 py-2 font-medium">Score</th>
                <th className="text-left px-3 py-2 font-medium">Detected</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((a: AnomalyResultResponse) => {
                const classification =
                  a.classification ||
                  a.details_json?.classification ||
                  (a.detector_type === 'DFA'
                    ? 'SYNTACTIC_ANOMALY'
                    : a.detector_type === 'ISOLATION_FOREST'
                      ? 'BEHAVIORAL_ANOMALY'
                      : 'COMPOUND_ANOMALY');
                return (
                  <tr
                    key={a.id}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-3 py-2 font-mono text-slate-400">
                      {a.case_id.slice(0, 10)}…
                    </td>
                    <td className="px-3 py-2">
                      <ClassificationBadge classification={classification} />
                    </td>
                    <td className="px-3 py-2">
                      <SeverityDot severity={a.severity} />
                    </td>
                    <td className="px-3 py-2 text-slate-400">{a.detector_type}</td>
                    <td className="px-3 py-2 font-mono text-slate-400">
                      {a.anomaly_score?.toFixed(4) ?? '—'}
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {new Date(a.detected_at).toLocaleTimeString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-slate-500 text-xs">
          No anomalies recorded yet. Submit events with the simulator to generate data.
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 bg-slate-800 border border-slate-700 rounded disabled:opacity-30 hover:bg-slate-700 transition-colors"
          >
            <ChevronLeft size={12} className="text-slate-400" />
          </button>
          <span className="text-[10px] text-slate-500">
            Page {data.page} of {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page >= data.pages}
            className="p-1.5 bg-slate-800 border border-slate-700 rounded disabled:opacity-30 hover:bg-slate-700 transition-colors"
          >
            <ChevronRight size={12} className="text-slate-400" />
          </button>
        </div>
      )}
    </div>
  );
};

const SeverityDot: React.FC<{ severity: string }> = ({ severity }) => {
  const dotColor: Record<string, string> = {
    LOW: 'bg-slate-400',
    MEDIUM: 'bg-amber-400',
    HIGH: 'bg-orange-400',
    CRITICAL: 'bg-red-400',
  };
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor[severity] ?? 'bg-slate-400'}`} />
      <span className="text-slate-400">{severity}</span>
    </div>
  );
};
