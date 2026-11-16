import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  MarkerType,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { WorkflowResponse } from '../../types';
import { WorkflowNode } from './WorkflowNode';
import { Network, Sparkles } from 'lucide-react';

interface Props {
  workflow: WorkflowResponse | null;
  currentState?: string | null;
  visitedStates?: string[];
  highlightedTransition?: { from: string; event: string; to: string } | null;
}

// Clear structured layout for the Online Payment Automaton
const STATE_POSITIONS: Record<string, { x: number; y: number }> = {
  ORDER_CREATED: { x: 380, y: 15 },
  PAYMENT_INITIATED: { x: 380, y: 155 },
  PAYMENT_VERIFYING: { x: 380, y: 295 },
  ORDER_CONFIRMED: { x: 180, y: 460 },
  PAYMENT_FAILED: { x: 580, y: 460 },
  ORDER_CANCELLED: { x: 80, y: 620 },
  TRAP_STATE: { x: 680, y: 620 },
};

function getPosition(stateKey: string, index: number) {
  return (
    STATE_POSITIONS[stateKey] ?? {
      x: 100 + (index % 4) * 200,
      y: Math.floor(index / 4) * 160,
    }
  );
}

export const WorkflowCanvas: React.FC<Props> = ({
  workflow,
  currentState,
  visitedStates = [],
  highlightedTransition,
}) => {
  const nodeTypes: NodeTypes = useMemo(() => ({ workflow: WorkflowNode }), []);

  const buildNodes = useCallback((): Node[] => {
    if (!workflow) return [];
    return workflow.states.map((s, i) => ({
      id: s.state_key,
      type: 'workflow',
      position: getPosition(s.state_key, i),
      data: {
        label: s.state_name || s.state_key,
        stateKey: s.state_key,
        stateType: s.state_type,
        isInitial: s.is_initial,
        isTerminal: s.is_terminal,
        isCurrent: currentState === s.state_key,
        isVisited: visitedStates.includes(s.state_key),
      },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }));
  }, [workflow, currentState, visitedStates]);

  const buildEdges = useCallback((): Edge[] => {
    if (!workflow) return [];
    const stateIdToKey = new Map<number, string>();
    workflow.states.forEach((s) => stateIdToKey.set(s.id, s.state_key));

    return workflow.transitions.map((t, i) => {
      const fromKey = t.from_state_key || stateIdToKey.get(t.from_state_id) || '';
      const toKey = t.to_state_key || stateIdToKey.get(t.to_state_id) || '';
      const isHighlighted =
        highlightedTransition &&
        highlightedTransition.from === fromKey &&
        highlightedTransition.event === t.event_name &&
        highlightedTransition.to === toKey;

      const isRetry =
        t.is_retry_transition ??
        (t.max_retries > 0 || t.event_name.includes('RETRY'));

      const strokeColor = isHighlighted
        ? '#38bdf8'
        : isRetry
          ? '#f59e0b'
          : '#475569';

      return {
        id: `e-${i}-${fromKey}-${toKey}`,
        source: fromKey,
        target: toKey,
        label: t.event_name.replace(/_/g, ' '),
        type: 'smoothstep',
        animated: !!isHighlighted,
        style: {
          stroke: strokeColor,
          strokeWidth: isHighlighted ? 2.5 : 1.5,
          strokeDasharray: isRetry && !isHighlighted ? '5 5' : undefined,
        },
        labelStyle: {
          fill: isHighlighted ? '#38bdf8' : '#94a3b8',
          fontSize: 9.5,
          fontFamily: 'monospace',
          fontWeight: isHighlighted ? 700 : 500,
        },
        labelBgStyle: {
          fill: isHighlighted ? '#082f49' : '#0f172a',
          fillOpacity: 0.95,
          stroke: isHighlighted ? '#0284c7' : '#334155',
          strokeWidth: 1,
        },
        labelBgPadding: [6, 4] as [number, number],
        labelBgBorderRadius: 5,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
          width: 15,
          height: 15,
        },
      };
    });
  }, [workflow, highlightedTransition]);

  const [nodes, setNodes, onNodesChange] = useNodesState(buildNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState(buildEdges());

  React.useEffect(() => {
    setNodes(buildNodes());
    setEdges(buildEdges());
  }, [buildNodes, buildEdges, setNodes, setEdges]);

  if (!workflow) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm gap-2">
        <Network size={24} className="animate-pulse text-blue-400" />
        <span>Loading DFA Automaton Graph...</span>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden border border-slate-800/80 bg-slate-950/80 shadow-2xl backdrop-blur-xl">
      {/* Floating TOC Header / Legend */}
      <div className="absolute top-3 left-3 z-10 flex flex-col gap-2 pointer-events-none">
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl px-3.5 py-2.5 shadow-xl backdrop-blur-md pointer-events-auto">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles size={13} className="text-blue-400" />
            <h3 className="text-xs font-bold text-slate-200 tracking-wide">
              Automaton Architecture
            </h3>
            <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
              M = (Q, Σ, δ, q₀, F)
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
              <span className="text-slate-300">Start (q₀)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-600" />
              <span className="text-slate-400">Intermediate (Q)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
              <span className="text-slate-300">Accept (F₁)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" />
              <span className="text-slate-300">Cancel (F₂)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
              <span className="text-slate-300">Trap (q_err)</span>
            </div>
          </div>
        </div>

        {/* Current State Live Chip */}
        {currentState && (
          <div className="bg-slate-900/90 border border-blue-500/30 rounded-lg px-3 py-1.5 shadow-lg backdrop-blur-md flex items-center gap-2 pointer-events-auto w-fit">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400" />
            </span>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">Current Position:</span>
            <span className="text-[11px] font-mono font-bold text-blue-300">{currentState}</span>
          </div>
        )}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={22} size={1} />
        <Controls
          showInteractive={false}
          position="bottom-left"
          className="!bg-slate-900/90 !border !border-slate-800 !rounded-xl !overflow-hidden !shadow-xl"
        />
        <MiniMap
          nodeColor={(n) => {
            if (n.data?.isCurrent) return '#3b82f6';
            if (n.data?.isVisited) return '#6366f1';
            if (n.data?.stateType === 'TERMINAL_SUCCESS') return '#10b981';
            if (n.data?.stateType === 'TERMINAL_FAILURE') return '#f43f5e';
            if (n.data?.stateType === 'ERROR') return '#f59e0b';
            return '#475569';
          }}
          maskColor="rgba(15, 23, 42, 0.85)"
          position="bottom-right"
          className="!bg-slate-900/90 !border !border-slate-800 !rounded-xl !overflow-hidden !shadow-xl"
        />
      </ReactFlow>
    </div>
  );
};
