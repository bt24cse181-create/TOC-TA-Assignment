import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Circle,
  Radio,
} from 'lucide-react';

interface WorkflowNodeData {
  label: string;
  stateKey: string;
  stateType: string;
  isInitial: boolean;
  isTerminal: boolean;
  isCurrent: boolean;
  isVisited: boolean;
  [key: string]: unknown;
}

const stateConfig: Record<
  string,
  {
    icon: React.ComponentType<{ size?: number; className?: string }>;
    borderColor: string;
    bgColor: string;
    textColor: string;
    badgeBg: string;
    badgeText: string;
    badgeLabel: string;
    glow: string;
  }
> = {
  START: {
    icon: Play,
    borderColor: 'border-blue-500/80',
    bgColor: 'bg-gradient-to-b from-blue-950/70 to-slate-900/90',
    textColor: 'text-blue-300',
    badgeBg: 'bg-blue-500/20 border-blue-500/40',
    badgeText: 'text-blue-300',
    badgeLabel: 'START (q₀)',
    glow: 'shadow-[0_0_18px_rgba(59,130,246,0.35)]',
  },
  INTERMEDIATE: {
    icon: Circle,
    borderColor: 'border-slate-700 hover:border-slate-500',
    bgColor: 'bg-gradient-to-b from-slate-900/90 to-slate-950/90',
    textColor: 'text-slate-200',
    badgeBg: 'bg-slate-800/80 border-slate-700',
    badgeText: 'text-slate-400',
    badgeLabel: 'STATE',
    glow: 'shadow-lg',
  },
  TERMINAL_SUCCESS: {
    icon: CheckCircle2,
    borderColor: 'border-emerald-500/80',
    bgColor: 'bg-gradient-to-b from-emerald-950/70 to-slate-900/90',
    textColor: 'text-emerald-300',
    badgeBg: 'bg-emerald-500/20 border-emerald-500/40',
    badgeText: 'text-emerald-300',
    badgeLabel: 'ACCEPT (F₁)',
    glow: 'shadow-[0_0_18px_rgba(16,185,129,0.35)]',
  },
  TERMINAL_FAILURE: {
    icon: XCircle,
    borderColor: 'border-rose-500/80',
    bgColor: 'bg-gradient-to-b from-rose-950/70 to-slate-900/90',
    textColor: 'text-rose-300',
    badgeBg: 'bg-rose-500/20 border-rose-500/40',
    badgeText: 'text-rose-300',
    badgeLabel: 'CANCEL (F₂)',
    glow: 'shadow-[0_0_18px_rgba(244,63,94,0.35)]',
  },
  ERROR: {
    icon: AlertTriangle,
    borderColor: 'border-amber-500/80',
    bgColor: 'bg-gradient-to-b from-amber-950/70 to-slate-900/90',
    textColor: 'text-amber-300',
    badgeBg: 'bg-amber-500/20 border-amber-500/40',
    badgeText: 'text-amber-300',
    badgeLabel: 'TRAP STATE (q_err)',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.4)]',
  },
};

const WorkflowNodeComponent: React.FC<NodeProps> = ({ data }) => {
  const d = data as unknown as WorkflowNodeData;
  const cfg = stateConfig[d.stateType] || stateConfig.INTERMEDIATE;
  const Icon = cfg.icon;

  const currentStyles = d.isCurrent
    ? 'ring-2 ring-blue-400 ring-offset-2 ring-offset-slate-950 shadow-[0_0_25px_rgba(59,130,246,0.6)] animate-pulse'
    : '';

  const visitedStyles =
    d.isVisited && !d.isCurrent
      ? 'border-indigo-400/80 shadow-[0_0_12px_rgba(99,102,241,0.25)]'
      : '';

  return (
    <div className="relative group">
      {/* Handle Target (Incoming) */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-500 !border-2 !border-slate-800 !w-2.5 !h-2.5 !-top-1.5 transition-colors group-hover:!bg-blue-400"
      />

      {/* Main Node Card */}
      <div
        className={`
          px-4 py-3 rounded-xl border-[1.5px] min-w-[170px] backdrop-blur-md
          transition-all duration-300 select-none
          ${cfg.borderColor} ${cfg.bgColor} ${cfg.glow}
          ${currentStyles} ${visitedStyles}
        `}
      >
        {/* Top meta badge */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <span
            className={`text-[8.5px] uppercase font-mono font-bold tracking-wider px-1.5 py-0.5 rounded-full border ${cfg.badgeBg} ${cfg.badgeText}`}
          >
            {cfg.badgeLabel}
          </span>
          {d.isCurrent && (
            <span className="flex items-center gap-1 text-[9px] font-bold text-blue-400 bg-blue-500/20 px-1.5 py-0.5 rounded-full border border-blue-500/40 animate-pulse">
              <Radio size={9} className="animate-spin text-blue-400" /> ACTIVE
            </span>
          )}
          {d.isVisited && !d.isCurrent && (
            <span className="text-[8.5px] font-mono text-indigo-400 bg-indigo-500/10 px-1 rounded">
              VISITED
            </span>
          )}
        </div>

        {/* State Title */}
        <div className="flex items-center justify-center gap-2">
          <Icon size={14} className={cfg.textColor} />
          <span className={`text-xs font-bold tracking-wide ${cfg.textColor}`}>
            {d.label}
          </span>
        </div>

        {/* State Key Technical Subtitle */}
        <div className="mt-1 text-[9.5px] text-slate-400/90 font-mono text-center">
          {d.stateKey}
        </div>
      </div>

      {/* Handle Source (Outgoing) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-500 !border-2 !border-slate-800 !w-2.5 !h-2.5 !-bottom-1.5 transition-colors group-hover:!bg-blue-400"
      />
    </div>
  );
};

export const WorkflowNode = memo(WorkflowNodeComponent);
