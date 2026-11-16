import React, { useState } from 'react';
import {
  Play,
  Loader2,
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { runBatchSimulation } from '../../api/client';
import type { BatchSimulationResponse, SimulationCaseInput } from '../../types';
import { ClassificationBadge } from '../Simulator/EventSimulator';

// ─── Preset Scenarios ─────────────────────────────────────────────────────────

const PRESETS: Record<string, { label: string; description: string; cases: SimulationCaseInput[] }> = {
  normal_happy_path: {
    label: 'Normal Happy Path ×10',
    description: '10 standard successful payment flows',
    cases: Array.from({ length: 10 }, () => ({
      events: [
        { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 1100 + Math.floor(Math.random() * 400) },
        { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 800 + Math.floor(Math.random() * 600) },
        { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1000 + Math.floor(Math.random() * 500) },
      ],
      total_amount: 500 + Math.floor(Math.random() * 9500),
    })),
  },
  cancellation_flow: {
    label: 'Cancellation Flow ×5',
    description: '5 order cancellations at different stages',
    cases: Array.from({ length: 5 }, () => ({
      events: [
        { event_name: 'CANCEL_ORDER', execution_duration_ms: 1200 },
      ],
      total_amount: 1000 + Math.floor(Math.random() * 4000),
    })),
  },
  retry_flow: {
    label: 'Retry + Success ×5',
    description: '5 cases with payment failure and successful retry',
    cases: Array.from({ length: 5 }, () => ({
      events: [
        { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 1200 },
        { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 1000 },
        { event_name: 'PAYMENT_FAILURE', execution_duration_ms: 900 },
        { event_name: 'RETRY_PAYMENT', execution_duration_ms: 1100 },
        { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 1000 },
        { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1200 },
      ],
      total_amount: 2000 + Math.floor(Math.random() * 5000),
    })),
  },
  bot_speed: {
    label: 'Bot Speed ×10',
    description: '10 suspiciously fast (10–30ms) payment completions',
    cases: Array.from({ length: 10 }, () => ({
      events: [
        { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 15 },
        { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 12 },
        { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 18 },
      ],
      total_amount: 50000 + Math.floor(Math.random() * 50000),
    })),
  },
  invalid_trace: {
    label: 'Invalid Traces ×5',
    description: '5 cases with DFA-violating event sequences',
    cases: Array.from({ length: 5 }, () => ({
      events: [
        { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1200 },
      ],
      total_amount: 3000,
    })),
  },
  mixed: {
    label: 'Mixed Scenario ×20',
    description: '20 cases: mix of normal, bot-speed, retries, and invalid',
    cases: [
      // 8 normal
      ...Array.from({ length: 8 }, () => ({
        events: [
          { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 1100 + Math.floor(Math.random() * 400) },
          { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 900 + Math.floor(Math.random() * 500) },
          { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1000 + Math.floor(Math.random() * 400) },
        ],
        total_amount: 1000 + Math.floor(Math.random() * 5000),
      })),
      // 4 bot
      ...Array.from({ length: 4 }, () => ({
        events: [
          { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 15 },
          { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 10 },
          { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 12 },
        ],
        total_amount: 80000 + Math.floor(Math.random() * 20000),
      })),
      // 4 retry
      ...Array.from({ length: 4 }, () => ({
        events: [
          { event_name: 'INITIATE_PAYMENT', execution_duration_ms: 1200 },
          { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 1000 },
          { event_name: 'PAYMENT_FAILURE', execution_duration_ms: 900 },
          { event_name: 'RETRY_PAYMENT', execution_duration_ms: 1100 },
          { event_name: 'VERIFY_PAYMENT', execution_duration_ms: 1000 },
          { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1200 },
        ],
        total_amount: 3000 + Math.floor(Math.random() * 5000),
      })),
      // 4 invalid
      ...Array.from({ length: 4 }, () => ({
        events: [
          { event_name: 'PAYMENT_SUCCESS', execution_duration_ms: 1200 },
        ],
        total_amount: 5000,
      })),
    ],
  },
};

export const BatchSimulator: React.FC = () => {
  const [result, setResult] = useState<BatchSimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState('mixed');

  const handleRun = async () => {
    const preset = PRESETS[selectedPreset];
    if (!preset) return;
    try {
      setLoading(true);
      setError(null);
      const resp = await runBatchSimulation({
        workflow_code: 'ONLINE_PAYMENT',
        cases: preset.cases,
        persist_results: true,
      });
      setResult(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5">
        <BarChart3 size={15} className="text-blue-400" />
        Batch Simulation
      </h2>

      {/* Preset Selector */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
        <h3 className="text-xs font-semibold text-slate-300">Select Scenario</h3>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(PRESETS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => setSelectedPreset(key)}
              className={`text-left px-3 py-2 rounded-md border text-[11px] transition-colors ${
                selectedPreset === key
                  ? 'bg-blue-500/15 border-blue-500/30 text-blue-300'
                  : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-300'
              }`}
            >
              <span className="font-medium block">{preset.label}</span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                {preset.description}
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-md text-xs font-medium text-white transition-colors flex items-center justify-center gap-1.5"
        >
          {loading ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <Play size={13} />
          )}
          Run Batch Simulation
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <p className="text-[11px] text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-3">
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-2">
            <SummaryCard
              label="Total Cases"
              value={result.total_cases}
              icon={BarChart3}
              color="text-blue-400"
            />
            <SummaryCard
              label="Normal"
              value={result.normal_count}
              icon={CheckCircle2}
              color="text-emerald-400"
            />
            <SummaryCard
              label="Anomalies"
              value={result.anomaly_count}
              icon={AlertTriangle}
              color="text-red-400"
            />
          </div>

          {/* Distribution Bar */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
            <h4 className="text-[10px] text-slate-400 mb-2 uppercase tracking-wider font-semibold">
              Detection Rate
            </h4>
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden flex">
              <div
                className="bg-emerald-500 h-full transition-all"
                style={{
                  width: `${(result.normal_count / result.total_cases) * 100}%`,
                }}
                title={`Normal: ${result.normal_count}`}
              />
              <div
                className="bg-red-500 h-full transition-all"
                style={{
                  width: `${(result.anomaly_count / result.total_cases) * 100}%`,
                }}
                title={`Anomalies: ${result.anomaly_count}`}
              />
            </div>
            <div className="flex justify-between text-[9px] text-slate-500 mt-1">
              <span>Normal: {((result.normal_count / result.total_cases) * 100).toFixed(1)}%</span>
              <span>Anomalies: {((result.anomaly_count / result.total_cases) * 100).toFixed(1)}%</span>
            </div>
          </div>

          {/* Individual Results */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg overflow-hidden">
            <div className="max-h-[400px] overflow-y-auto">
              <table className="w-full text-[11px]">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="border-b border-slate-800 text-slate-500">
                    <th className="text-left px-3 py-2 font-medium">#</th>
                    <th className="text-left px-3 py-2 font-medium">Case ID</th>
                    <th className="text-left px-3 py-2 font-medium">
                      Classification
                    </th>
                    <th className="text-left px-3 py-2 font-medium">Severity</th>
                    <th className="text-left px-3 py-2 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r, i) => (
                    <tr
                      key={r.case_id}
                      className={`border-b border-slate-800/50 ${
                        r.is_anomaly ? 'bg-red-500/[0.03]' : ''
                      }`}
                    >
                      <td className="px-3 py-1.5 text-slate-500">{i + 1}</td>
                      <td className="px-3 py-1.5 font-mono text-slate-400">
                        {r.case_id.slice(0, 10)}…
                      </td>
                      <td className="px-3 py-1.5">
                        <ClassificationBadge classification={r.classification} />
                      </td>
                      <td className="px-3 py-1.5 text-slate-400">
                        {r.severity}
                      </td>
                      <td className="px-3 py-1.5">
                        {r.is_anomaly ? (
                          <XCircle size={12} className="text-red-400" />
                        ) : (
                          <CheckCircle2 size={12} className="text-emerald-400" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Summary Card ─────────────────────────────────────────────────────────────

const SummaryCard: React.FC<{
  label: string;
  value: number;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
}> = ({ label, value, icon: Icon, color }) => (
  <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-center">
    <Icon size={16} className={`${color} mx-auto mb-1`} />
    <p className="text-lg font-bold text-slate-200">{value}</p>
    <p className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</p>
  </div>
);
