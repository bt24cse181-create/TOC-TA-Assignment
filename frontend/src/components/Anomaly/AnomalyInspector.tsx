import React from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Binary,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { HybridEvaluation } from '../../types';

interface Props {
  evaluation: HybridEvaluation | null;
}

export const AnomalyInspector: React.FC<Props> = ({ evaluation }) => {
  if (!evaluation) {
    return (
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex flex-col items-center justify-center text-center min-h-[220px] shadow-lg">
        <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center mb-3">
          <Shield size={24} className="text-slate-500" />
        </div>
        <p className="text-xs font-semibold text-slate-300">
          Awaiting Case Telemetry
        </p>
        <p className="text-[10.5px] text-slate-500 mt-1 max-w-[260px] leading-relaxed">
          Drive the workflow or select a 1-click viva preset above to evaluate DFA rules and ML anomaly scores in real-time.
        </p>
      </div>
    );
  }

  const classConfig: Record<
    string,
    {
      icon: React.ComponentType<{ size?: number; className?: string }>;
      color: string;
      bg: string;
      border: string;
      badge: string;
      label: string;
      sublabel: string;
    }
  > = {
    NORMAL: {
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bg: 'bg-emerald-950/20',
      border: 'border-emerald-500/40',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      label: 'Verified Normal Execution',
      sublabel: 'DFA Valid & ML Score Within Normal Bounds',
    },
    SYNTACTIC_ANOMALY: {
      icon: ShieldAlert,
      color: 'text-rose-400',
      bg: 'bg-rose-950/25',
      border: 'border-rose-500/50',
      badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
      label: 'Syntactic Anomaly (DFA Violation)',
      sublabel: 'Formal Automata Rejection — Illegal Transition',
    },
    BEHAVIORAL_ANOMALY: {
      icon: AlertTriangle,
      color: 'text-amber-400',
      bg: 'bg-amber-950/25',
      border: 'border-amber-500/50',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      label: 'Behavioral Anomaly (ML Outlier)',
      sublabel: 'Grammatically Valid but Statistically Abnormal',
    },
    COMPOUND_ANOMALY: {
      icon: ShieldAlert,
      color: 'text-purple-400',
      bg: 'bg-purple-950/25',
      border: 'border-purple-500/50',
      badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      label: 'Compound Anomaly (DFA + ML)',
      sublabel: 'Concurrent Automata Violation and ML Outlier',
    },
  };

  const cfg = classConfig[evaluation.classification] ?? classConfig.NORMAL;
  const Icon = cfg.icon;

  // Threshold position percentage on the bar
  const thresholdPct = Math.round(evaluation.ml.threshold * 100);
  const scorePct = Math.min(Math.max(Math.round(evaluation.ml.score * 100), 2), 100);

  return (
    <div className="space-y-3">
      {/* Classification Banner Card */}
      <div className={`${cfg.bg} border ${cfg.border} rounded-xl p-3.5 shadow-xl transition-all`}>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg ${cfg.bg} border ${cfg.border}`}>
              <Icon size={18} className={cfg.color} />
            </div>
            <div>
              <h4 className={`text-xs font-bold tracking-wide ${cfg.color}`}>
                {cfg.label}
              </h4>
              <p className="text-[9.5px] text-slate-400 font-mono">
                {cfg.sublabel}
              </p>
            </div>
          </div>
          <SeverityBadge severity={evaluation.severity} />
        </div>

        {/* Human-readable explanation */}
        <p className="text-[11px] text-slate-200 leading-relaxed bg-slate-950/60 p-2 rounded-lg border border-slate-800/80">
          {evaluation.explanation}
        </p>

        {/* State Tags */}
        <div className="flex items-center gap-2 mt-2 text-[9.5px]">
          <span className="text-slate-400 font-mono">Automaton State:</span>
          <span className="font-mono font-bold text-blue-300 bg-blue-500/20 px-2 py-0.5 rounded border border-blue-500/30">
            {evaluation.final_state}
          </span>
          {evaluation.is_partial && (
            <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded font-mono">
              IN PROGRESS
            </span>
          )}
          {evaluation.is_completed && (
            <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded font-mono">
              TERMINATED
            </span>
          )}
        </div>
      </div>

      {/* Side-by-Side Verification Engines */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* DFA Automata Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Binary size={11} className="text-blue-400" />
              Automata (TOC)
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                evaluation.dfa.is_valid
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {evaluation.dfa.is_valid ? 'VALID δ' : 'REJECTED'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 mb-1.5">
            {evaluation.dfa.is_valid ? (
              <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
            ) : (
              <XCircle size={13} className="text-rose-400 shrink-0" />
            )}
            <span
              className={`text-[11px] font-bold ${
                evaluation.dfa.is_valid ? 'text-emerald-300' : 'text-rose-300'
              }`}
            >
              {evaluation.dfa.is_valid ? 'Grammar Satisfied' : 'Rule Violation'}
            </span>
          </div>

          {evaluation.dfa.message && (
            <p className="text-[10px] text-slate-400 leading-tight">
              {evaluation.dfa.message}
            </p>
          )}

          {evaluation.dfa.invalid_event && (
            <div className="mt-2 pt-2 border-t border-slate-800/80 space-y-1 text-[9.5px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Bad Symbol:</span>
                <span className="text-rose-400 font-mono font-bold">
                  {evaluation.dfa.invalid_event}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">From State:</span>
                <span className="text-slate-300 font-mono">
                  {evaluation.dfa.state_before_violation}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Error Code:</span>
                <span className="text-rose-400 font-mono text-[9px]">
                  {evaluation.dfa.error_type}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Machine Learning Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <TrendingUp size={11} className="text-amber-400" />
              Isolation Forest
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                evaluation.ml.is_anomaly
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              }`}
            >
              {evaluation.ml.is_anomaly ? 'OUTLIER' : 'NORMAL'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 mb-1.5">
            {evaluation.ml.is_anomaly ? (
              <AlertTriangle size={13} className="text-amber-400 shrink-0" />
            ) : (
              <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
            )}
            <span
              className={`text-[11px] font-bold ${
                evaluation.ml.is_anomaly ? 'text-amber-300' : 'text-emerald-300'
              }`}
            >
              {evaluation.ml.is_anomaly ? 'Statistical Anomaly' : 'Normal Pattern'}
            </span>
          </div>

          {/* Calibrated Threshold Visual Gauge */}
          <div className="mt-2 space-y-1">
            <div className="flex justify-between text-[9.5px]">
              <span className="text-slate-400">Score: <strong className="text-slate-200 font-mono">{evaluation.ml.score.toFixed(4)}</strong></span>
              <span className="text-slate-500 font-mono">Limit: {evaluation.ml.threshold.toFixed(4)}</span>
            </div>

            <div className="relative w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              {/* Score bar */}
              <div
                className={`h-full transition-all duration-500 ${
                  evaluation.ml.is_anomaly
                    ? 'bg-gradient-to-r from-amber-500 to-rose-500'
                    : 'bg-gradient-to-r from-blue-500 to-emerald-500'
                }`}
                style={{ width: `${scorePct}%` }}
              />
              {/* Threshold indicator marker */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-rose-400 shadow-[0_0_6px_rgba(244,63,94,0.9)]"
                style={{ left: `${thresholdPct}%` }}
                title={`Threshold: ${evaluation.ml.threshold.toFixed(4)}`}
              />
            </div>
            <div className="flex justify-between text-[8px] text-slate-500 font-mono">
              <span>0.00 (Normal)</span>
              <span className="text-rose-400">Threshold ({thresholdPct}%)</span>
              <span>1.00 (Outlier)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Feature Telemetry Deviations */}
      {evaluation.ml.top_contributing_features?.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles size={11} className="text-indigo-400" />
              Key Telemetry Drivers (Z-Score Standard Deviations)
            </span>
            <span className="text-[9px] text-slate-500">Outlier threshold: |z| &gt; 3.0</span>
          </div>
          <div className="space-y-1.5">
            {evaluation.ml.top_contributing_features.slice(0, 4).map(([name, z], idx) => {
              const isSignificant = Math.abs(z) > 3.0;
              return (
                <div key={idx} className="flex items-center justify-between text-[10px] bg-slate-950/60 px-2 py-1.5 rounded-lg border border-slate-800/80">
                  <span className="font-mono text-slate-300 truncate max-w-[190px]">
                    {name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`font-mono font-bold px-1.5 py-0.5 rounded text-[9.5px] ${
                        isSignificant
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'text-slate-400'
                      }`}
                    >
                      {z > 0 ? `+${z.toFixed(2)}σ` : `${z.toFixed(2)}σ`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Visited State Sequence Track */}
      {evaluation.visited_states?.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2 flex items-center gap-1">
            <Layers size={11} className="text-blue-400" />
            Complete State Path
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            {evaluation.visited_states.map((s, i) => (
              <React.Fragment key={i}>
                <span
                  className={`text-[9.5px] px-2 py-0.5 rounded-md font-mono font-medium ${
                    s === evaluation.final_state
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm'
                      : 'bg-slate-800/80 text-slate-400 border border-slate-700/60'
                  }`}
                >
                  {s}
                </span>
                {i < evaluation.visited_states.length - 1 && (
                  <span className="text-slate-600 text-[10px]">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Severity Badge ───────────────────────────────────────────────────────────

const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const colors: Record<string, string> = {
    LOW: 'bg-slate-800 text-slate-300 border-slate-700',
    MEDIUM: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    HIGH: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
    CRITICAL: 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-[0_0_10px_rgba(244,63,94,0.3)]',
  };
  return (
    <span
      className={`text-[9.5px] px-2 py-0.5 rounded-full font-mono font-bold border ${
        colors[severity] ?? colors.LOW
      }`}
    >
      {severity}
    </span>
  );
};
