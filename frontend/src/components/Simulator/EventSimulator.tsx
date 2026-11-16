import React, { useState, useMemo } from 'react';
import {
  Play,
  Plus,
  Zap,
  RotateCcw,
  ArrowRight,
  Bot,
  Loader2,
  AlertOctagon,
  ShieldAlert,
  Flame,
  CheckCircle,
} from 'lucide-react';
import type {
  CaseResponse,
  EventSubmissionResponse,
  WorkflowResponse,
  WorkflowTransitionResponse,
} from '../../types';
import type { ScenarioConfig } from '../../hooks/useCase';

interface Props {
  workflow: WorkflowResponse | null;
  activeCase: CaseResponse | null;
  loading: boolean;
  error: string | null;
  eventHistory: EventSubmissionResponse[];
  onCreateCase: (amount?: number, userId?: string) => void;
  onSendEvent: (eventName: string, durationMs?: number) => void;
  onRunScenario: (config: ScenarioConfig) => Promise<void>;
  onClearCase: () => void;
}

const DEFAULT_DURATION = 1200;
const BOT_DURATION = 15;

export const EventSimulator: React.FC<Props> = ({
  workflow,
  activeCase,
  loading,
  error,
  eventHistory,
  onCreateCase,
  onSendEvent,
  onRunScenario,
  onClearCase,
}) => {
  const [amount, setAmount] = useState('250');
  const [userId, setUserId] = useState('user_demo_1');
  const [botSpeed, setBotSpeed] = useState(false);
  const [customDuration, setCustomDuration] = useState(String(DEFAULT_DURATION));
  const [activeTab, setActiveTab] = useState<'transitions' | 'violations' | 'presets'>('transitions');
  const [autoRunning, setAutoRunning] = useState(false);

  // Map state ID to state key for resilient lookup
  const stateIdToKey = useMemo(() => {
    const map = new Map<number, string>();
    workflow?.states.forEach((s) => map.set(s.id, s.state_key));
    return map;
  }, [workflow]);

  // Complete Alphabet Sigma from workflow
  const fullAlphabet: string[] = useMemo(() => {
    if (!workflow) return [];
    const set = new Set<string>();
    workflow.transitions.forEach((t) => set.add(t.event_name));
    return Array.from(set);
  }, [workflow]);

  // Allowed transitions from current state
  const availableTransitions: WorkflowTransitionResponse[] = useMemo(() => {
    if (!workflow || !activeCase) return [];
    return workflow.transitions.filter((t) => {
      const fromKey = t.from_state_key || stateIdToKey.get(t.from_state_id);
      return fromKey === activeCase.current_state_key;
    });
  }, [workflow, activeCase, stateIdToKey]);

  // Allowed event names from current state
  const allowedEventNames = useMemo(
    () => new Set(availableTransitions.map((t) => t.event_name)),
    [availableTransitions]
  );

  // Illegal / Forbidden events from current state (DFA Test Violations)
  const illegalEvents: string[] = useMemo(() => {
    if (!activeCase) return [];
    return fullAlphabet.filter((e) => !allowedEventNames.has(e));
  }, [activeCase, fullAlphabet, allowedEventNames]);

  const isTerminal =
    activeCase &&
    workflow?.states.find((s) => s.state_key === activeCase.current_state_key)
      ?.is_terminal;

  const handleSendEvent = (eventName: string, forceDuration?: number) => {
    const durationMs =
      forceDuration !== undefined
        ? forceDuration
        : botSpeed
          ? BOT_DURATION
          : parseInt(customDuration) || DEFAULT_DURATION;
    onSendEvent(eventName, durationMs);
  };

  // 1-Click Viva Attack Presets Runner
  const runPresetScenario = async (scenario: 'happy' | 'dfa_attack' | 'bot_attack') => {
    setAutoRunning(true);
    try {
      if (scenario === 'happy') {
        // Standard legitimate payment flow: realistic amounts & human duration -> NORMAL
        await onRunScenario({
          workflowCode: workflow?.code || 'ONLINE_PAYMENT',
          amount: 250,
          userId: 'normal_customer',
          events: [
            { event_name: 'INITIATE_PAYMENT', duration_ms: 1400 },
            { event_name: 'VERIFY_PAYMENT', duration_ms: 1200 },
            { event_name: 'PAYMENT_SUCCESS', duration_ms: 1100 },
          ],
        });
      } else if (scenario === 'dfa_attack') {
        // DFA Syntactic Violation: Attempts PAYMENT_SUCCESS directly from ORDER_CREATED
        await onRunScenario({
          workflowCode: workflow?.code || 'ONLINE_PAYMENT',
          amount: 250,
          userId: 'adversary_attacker',
          events: [
            { event_name: 'PAYMENT_SUCCESS', duration_ms: 1200 },
          ],
        });
      } else if (scenario === 'bot_attack') {
        // ML Behavioral Outlier: Grammatically valid steps, but extreme ₹85,000 + 15ms speed
        await onRunScenario({
          workflowCode: workflow?.code || 'ONLINE_PAYMENT',
          amount: 85000,
          userId: 'bot_trader_42',
          events: [
            { event_name: 'INITIATE_PAYMENT', duration_ms: 15 },
            { event_name: 'VERIFY_PAYMENT', duration_ms: 12 },
            { event_name: 'PAYMENT_SUCCESS', duration_ms: 18 },
          ],
        });
      }
    } finally {
      setAutoRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* 1-Click Viva Attack Presets Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10.5px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
            <Zap size={13} className="text-amber-400" />
            1-Click Viva Demonstrations
          </span>
          {autoRunning && (
            <span className="flex items-center gap-1 text-[10px] text-amber-400 animate-pulse">
              <Loader2 size={10} className="animate-spin" /> Running...
            </span>
          )}
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          <button
            onClick={() => runPresetScenario('happy')}
            disabled={loading || autoRunning}
            className="flex flex-col items-start p-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 transition-all text-left group disabled:opacity-40"
            title="Normal valid payment flow"
          >
            <div className="flex items-center gap-1 text-[10px] font-bold">
              <CheckCircle size={11} className="text-emerald-400" /> Happy Path
            </div>
            <span className="text-[8.5px] text-emerald-400/80 mt-0.5">
              Normal (DFA ✓ ML ✓)
            </span>
          </button>

          <button
            onClick={() => runPresetScenario('dfa_attack')}
            disabled={loading || autoRunning}
            className="flex flex-col items-start p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 transition-all text-left group disabled:opacity-40"
            title="DFA Violation: skip verification directly to PAYMENT_SUCCESS"
          >
            <div className="flex items-center gap-1 text-[10px] font-bold">
              <ShieldAlert size={11} className="text-rose-400" /> DFA Attack
            </div>
            <span className="text-[8.5px] text-rose-400/80 mt-0.5">
              Skip verify (Syntactic ✗)
            </span>
          </button>

          <button
            onClick={() => runPresetScenario('bot_attack')}
            disabled={loading || autoRunning}
            className="flex flex-col items-start p-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 transition-all text-left group disabled:opacity-40"
            title="ML Outlier: valid steps but 15ms velocity attack"
          >
            <div className="flex items-center gap-1 text-[10px] font-bold">
              <Flame size={11} className="text-amber-400" /> Bot Speed
            </div>
            <span className="text-[8.5px] text-amber-400/80 mt-0.5">
              15ms outlier (ML ✗)
            </span>
          </button>
        </div>
      </div>

      {/* Case Creation or Active Case Panel */}
      {!activeCase ? (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
          <h3 className="text-xs font-bold text-slate-200 mb-3 flex items-center gap-1.5">
            <Plus size={14} className="text-blue-400" />
            Initialize Process Instance
          </h3>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>Transaction Amount (₹)</span>
                <span className="text-slate-500">ML Feature</span>
              </div>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800/90 border border-slate-700/80 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="2500"
              />
            </div>
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>User Identifier</span>
                <span className="text-slate-500">Auditing</span>
              </div>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800/90 border border-slate-700/80 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="user_demo_1"
              />
            </div>
            <button
              onClick={() =>
                onCreateCase(parseFloat(amount) || undefined, userId || undefined)
              }
              disabled={loading || !workflow || autoRunning}
              className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-xs font-bold text-white transition-all shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2"
            >
              {loading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} fill="currentColor" />
              )}
              Start Workflow Instance
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Active Case Telemetry Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 shadow-xl">
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                <h3 className="text-xs font-bold text-slate-200">
                  Case Execution Telemetry
                </h3>
              </div>
              <button
                onClick={onClearCase}
                disabled={loading || autoRunning}
                className="text-[10px] text-slate-400 hover:text-rose-400 flex items-center gap-1 transition-colors px-2 py-0.5 bg-slate-800/60 rounded border border-slate-700/60"
              >
                <RotateCcw size={10} /> Reset Case
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
              <div>
                <span className="text-slate-500 text-[10px] block">Current State</span>
                <span className="font-mono font-bold text-blue-400 text-xs">
                  {activeCase.current_state_key}
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Status</span>
                <StatusBadge status={activeCase.status} />
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Amount</span>
                <span className="font-mono text-slate-300">
                  ₹{Number(activeCase.total_amount ?? 0).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Events / Retries</span>
                <span className="font-mono text-slate-300">
                  {activeCase.events.length} ev / {activeCase.retry_count} retries
                </span>
              </div>
            </div>
          </div>

          {/* Timing & Velocity Controls */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
                <Bot size={13} className="text-blue-400" />
                Telemetry Velocity Simulation
              </span>
              <button
                onClick={() => setBotSpeed(!botSpeed)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-bold border transition-all ${
                  botSpeed
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap size={11} className={botSpeed ? 'text-amber-400 fill-amber-400' : ''} />
                {botSpeed ? 'Bot Speed (15ms)' : 'Normal (1200ms)'}
              </button>
            </div>
            {!botSpeed && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400">Custom Delay:</span>
                <input
                  type="number"
                  value={customDuration}
                  onChange={(e) => setCustomDuration(e.target.value)}
                  className="w-24 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-[11px] font-mono text-slate-200 focus:outline-none focus:border-blue-500"
                />
                <span className="text-[10px] text-slate-500">ms / step</span>
              </div>
            )}
          </div>

          {/* Interactive Event Alphabet Driver */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 shadow-xl">
            {/* Tab navigation between Allowed and DFA Violations */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <div className="flex gap-1.5">
                <button
                  onClick={() => setActiveTab('transitions')}
                  className={`px-2.5 py-1 rounded-md text-[10.5px] font-bold transition-all ${
                    activeTab === 'transitions'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  Allowed Next ({availableTransitions.length})
                </button>
                <button
                  onClick={() => setActiveTab('violations')}
                  className={`px-2.5 py-1 rounded-md text-[10.5px] font-bold transition-all flex items-center gap-1 ${
                    activeTab === 'violations'
                      ? 'bg-rose-600 text-white shadow-md'
                      : 'text-rose-400 hover:bg-rose-500/10'
                  }`}
                >
                  <AlertOctagon size={11} />
                  Test DFA Violations ({illegalEvents.length})
                </button>
              </div>
            </div>

            {isTerminal ? (
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-center">
                <p className="text-xs font-semibold text-slate-300">
                  Terminal Automaton State Reached
                </p>
                <p className="text-[10px] text-slate-500 mt-1">
                  This execution is complete. Reset case to test another workflow path.
                </p>
              </div>
            ) : activeTab === 'transitions' ? (
              /* Allowed Transitions (Normal execution) */
              <div className="space-y-1.5">
                <p className="text-[9.5px] text-slate-500 mb-1 flex items-center gap-1">
                  <CheckCircle size={10} className="text-emerald-400" />
                  Mathematically valid transitions from {activeCase.current_state_key}:
                </p>
                {availableTransitions.map((t) => {
                  const toKey = t.to_state_key || stateIdToKey.get(t.to_state_id) || '';
                  const isRetry =
                    t.is_retry_transition ??
                    (t.max_retries > 0 || t.event_name.includes('RETRY'));
                  return (
                    <button
                      key={`${t.id || t.event_name}-${toKey}`}
                      onClick={() => handleSendEvent(t.event_name)}
                      disabled={loading || autoRunning}
                      className="w-full flex items-center justify-between px-3 py-2 bg-slate-800/80 hover:bg-blue-900/30 hover:border-blue-500/50 disabled:opacity-40 border border-slate-700/80 rounded-lg text-xs font-medium text-slate-200 hover:text-white transition-all group shadow-sm"
                    >
                      <span className="flex items-center gap-2">
                        <ArrowRight
                          size={12}
                          className="text-slate-400 group-hover:text-blue-400 transition-colors"
                        />
                        <span className="font-mono text-[11px] font-semibold">{t.event_name}</span>
                        {isRetry && (
                          <span className="text-[9px] px-1.5 py-0.2 bg-amber-500/20 text-amber-300 rounded border border-amber-500/40 font-mono">
                            retry
                          </span>
                        )}
                      </span>
                      <span className="text-[9.5px] text-slate-400 font-mono">
                        → {toKey}
                      </span>
                    </button>
                  );
                })}
                {availableTransitions.length === 0 && (
                  <p className="text-[11px] text-slate-500 text-center py-2">
                    No allowed outgoing transitions from this state.
                  </p>
                )}
              </div>
            ) : (
              /* Test DFA Violations (Illegal events from this state) */
              <div className="space-y-1.5">
                <p className="text-[9.5px] text-rose-400/90 mb-1 flex items-center gap-1 font-medium">
                  <AlertOctagon size={10} className="text-rose-400" />
                  1-Click Test: Click any event below to trigger an immediate DFA Syntactic Anomaly:
                </p>
                <div className="grid grid-cols-1 gap-1.5 max-h-48 overflow-y-auto pr-1">
                  {illegalEvents.map((eventName) => (
                    <button
                      key={eventName}
                      onClick={() => handleSendEvent(eventName)}
                      disabled={loading || autoRunning}
                      className="w-full flex items-center justify-between px-3 py-2 bg-rose-950/20 hover:bg-rose-900/40 border border-rose-500/30 hover:border-rose-500/60 rounded-lg text-xs text-rose-200 transition-all group disabled:opacity-40 shadow-sm"
                    >
                      <div className="flex items-center gap-1.5">
                        <ShieldAlert size={12} className="text-rose-400 group-hover:animate-bounce" />
                        <span className="font-mono text-[11px] font-bold">{eventName}</span>
                      </div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono border border-rose-500/30">
                        Illegal from {activeCase.current_state_key}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Execution Step Log */}
      {eventHistory.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 shadow-lg">
          <h3 className="text-xs font-bold text-slate-300 mb-2 flex items-center justify-between">
            <span>Execution Trace ({eventHistory.length})</span>
            <span className="text-[10px] font-mono text-slate-500">Event History</span>
          </h3>
          <div className="max-h-44 overflow-y-auto space-y-1.5 pr-1">
            {eventHistory.map((ev, i) => (
              <div
                key={i}
                className={`flex items-center justify-between px-2.5 py-2 rounded-lg text-[10.5px] border ${
                  ev.evaluation?.is_anomaly
                    ? 'bg-rose-500/10 border-rose-500/30'
                    : 'bg-slate-950/70 border-slate-800'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 font-mono text-[10px]">
                    #{i + 1}
                  </span>
                  <span className="text-slate-200 font-mono font-medium">
                    {ev.event.event_name}
                  </span>
                </div>
                <ClassificationBadge
                  classification={ev.evaluation?.classification ?? 'NORMAL'}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 shadow-lg">
          <p className="text-[11px] text-rose-400 font-medium">{error}</p>
        </div>
      )}
    </div>
  );
};

// ─── Badges ───────────────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    RUNNING: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    COMPLETED: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    FAILED: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    ANOMALOUS: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-[9.5px] font-mono font-bold border ${
        colors[status] ?? colors.RUNNING
      }`}
    >
      {status}
    </span>
  );
};

export const ClassificationBadge: React.FC<{ classification: string }> = ({
  classification,
}) => {
  const colors: Record<string, string> = {
    NORMAL: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    SYNTACTIC_ANOMALY: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    BEHAVIORAL_ANOMALY: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    COMPOUND_ANOMALY: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
  };
  const labels: Record<string, string> = {
    NORMAL: 'NORMAL',
    SYNTACTIC_ANOMALY: 'DFA VIOLATION',
    BEHAVIORAL_ANOMALY: 'ML OUTLIER',
    COMPOUND_ANOMALY: 'DFA + ML ALERT',
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-bold border ${
        colors[classification] ?? colors.NORMAL
      }`}
    >
      {labels[classification] ?? classification}
    </span>
  );
};
