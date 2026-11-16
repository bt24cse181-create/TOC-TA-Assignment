import React from 'react';
import {
  Activity,
  Shield,
  Wifi,
  WifiOff,
  Loader2,
  Database,
  Brain,
  Cpu,
  BarChart2,
} from 'lucide-react';
import type { ConnectionStatus } from '../../hooks/useHealth';
import type { HealthResponse } from '../../types';

interface Props {
  status: ConnectionStatus;
  health: HealthResponse | null;
  onRefresh: () => void;
}

export const HealthIndicator: React.FC<Props> = ({
  status,
  health,
  onRefresh,
}) => {
  const statusConfig = {
    connected: {
      icon: Wifi,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      label: 'System Online',
      dot: 'bg-emerald-400',
    },
    disconnected: {
      icon: WifiOff,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/30',
      label: 'Disconnected',
      dot: 'bg-rose-400',
    },
    checking: {
      icon: Loader2,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      label: 'Pinging...',
      dot: 'bg-amber-400',
    },
  };

  const cfg = statusConfig[status];
  const Icon = cfg.icon;

  return (
    <div
      className={`flex items-center gap-3 px-3 py-1.5 rounded-xl border ${cfg.bg} ${cfg.border} cursor-pointer hover:opacity-90 transition-all shadow-md backdrop-blur-md`}
      onClick={onRefresh}
      title="Click to refresh connection telemetry"
    >
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-75`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${cfg.dot}`}
          />
        </span>
        <Icon
          size={13}
          className={`${cfg.color} ${status === 'checking' ? 'animate-spin' : ''}`}
        />
        <span className={`text-[11px] font-bold ${cfg.color}`}>{cfg.label}</span>
      </div>

      {health && status === 'connected' && (
        <div className="flex items-center gap-2.5 ml-1 pl-2.5 border-l border-slate-700/80">
          <div className="flex items-center gap-1.5" title="MySQL Connection Status">
            <Database size={11} className="text-slate-400" />
            <span
              className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                health.database.status === 'connected'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : 'bg-rose-500/20 text-rose-300'
              }`}
            >
              MySQL
            </span>
          </div>
          <div className="flex items-center gap-1.5" title="Isolation Forest Model Status">
            <Brain size={11} className="text-slate-400" />
            <span
              className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                health.ml_engine.status === 'loaded'
                  ? 'bg-blue-500/20 text-blue-300'
                  : 'bg-rose-500/20 text-rose-300'
              }`}
            >
              ML Loaded (θ={health.ml_engine.threshold.toFixed(2)})
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Sidebar ──────────────────────────────────────────────────────────────────

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'simulator', label: 'Event Simulator', sub: 'Interactive DFA & ML', icon: Activity },
  { id: 'anomalies', label: 'Anomaly Log', sub: 'Detection Records', icon: Shield },
  { id: 'batch', label: 'Batch Simulation', sub: 'Bulk Test Vectors', icon: BarChart2 },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <div className="w-60 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between shrink-0 shadow-2xl backdrop-blur-xl">
      <div>
        {/* Project Branding */}
        <div className="px-4 py-5 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Shield size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-extrabold text-white tracking-wide flex items-center gap-1.5">
                WorkflowGuard
              </h1>
              <p className="text-[9.5px] text-blue-400 font-mono font-medium leading-tight">
                TOC + ML Hybrid Engine
              </p>
            </div>
          </div>
          <div className="mt-3 px-2 py-1 bg-slate-800/70 rounded-md border border-slate-700/60 text-[9px] text-slate-400 font-mono flex items-center justify-between">
            <span>Automaton: DFA</span>
            <span className="text-emerald-400">Deterministic</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="p-2.5 space-y-1.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${
                  isActive
                    ? 'bg-blue-600/15 text-white border border-blue-500/40 shadow-lg shadow-blue-500/10'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
                }`}
              >
                <div
                  className={`p-1.5 rounded-lg ${
                    isActive ? 'bg-blue-500 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  <Icon size={14} />
                </div>
                <div>
                  <span className="text-xs font-bold block">{tab.label}</span>
                  <span className="text-[9px] text-slate-500 block leading-tight">
                    {tab.sub}
                  </span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* College Project Viva Metadata Footer */}
      <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-semibold mb-1">
          <Cpu size={12} className="text-blue-400" />
          <span>Core Invariants</span>
        </div>
        <p className="text-[9px] text-slate-500 leading-relaxed font-mono">
          δ(q, σ) Transition Table<br />
          Isolation Forest (100 estimators)<br />
          Multi-vector Decision Policy
        </p>
        <div className="mt-2 text-[8.5px] text-slate-600 font-mono">
          Final Year CS Project Demo
        </div>
      </div>
    </div>
  );
};
