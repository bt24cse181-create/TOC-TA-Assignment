import { useState, useMemo } from 'react';
import { useHealth } from './hooks/useHealth';
import { useWorkflow } from './hooks/useWorkflow';
import { useCase } from './hooks/useCase';
import { HealthIndicator, Sidebar } from './components/Layout/DashboardLayout';
import { WorkflowCanvas } from './components/Workflow/WorkflowCanvas';
import { EventSimulator } from './components/Simulator/EventSimulator';
import { AnomalyInspector } from './components/Anomaly/AnomalyInspector';
import { AnomalyHistory } from './components/History/AnomalyHistory';
import { BatchSimulator } from './components/Simulation/BatchSimulator';
import type { ActiveTab } from './types';
import { GitBranch, ShieldAlert } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('simulator');
  const { health, status, refresh: refreshHealth } = useHealth();
  const { selectedWorkflow } = useWorkflow();
  const {
    activeCase,
    lastEvaluation,
    eventHistory,
    loading: caseLoading,
    error: caseError,
    startNewCase,
    sendEvent,
    runScenario,
    clearCase,
  } = useCase();

  // Highlight the active edge transition
  const highlightedTransition = useMemo(() => {
    if (!eventHistory.length) return null;
    const last = eventHistory[eventHistory.length - 1];
    if (!last.event.from_state_key || !last.event.to_state_key) return null;
    return {
      from: last.event.from_state_key,
      event: last.event.event_name,
      to: last.event.to_state_key,
    };
  }, [eventHistory]);

  const visitedStates = useMemo(
    () => lastEvaluation?.visited_states ?? (activeCase ? [activeCase.current_state_key] : []),
    [lastEvaluation, activeCase]
  );

  const handleCreateCase = (amount?: number, userId?: string) => {
    if (selectedWorkflow) {
      startNewCase(selectedWorkflow.code, amount, userId);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 font-sans text-slate-100 select-none">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={(t) => setActiveTab(t as ActiveTab)} />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between px-5 shrink-0 backdrop-blur-xl shadow-md z-20">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <GitBranch size={16} className="text-blue-400" />
              <h2 className="text-xs font-bold text-slate-200">
                {selectedWorkflow ? selectedWorkflow.name : 'Connecting to Workflow...'}
              </h2>
            </div>
            {selectedWorkflow && (
              <span className="text-[9.5px] font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700">
                v{selectedWorkflow.version}.0 • {selectedWorkflow.code}
              </span>
            )}
            {activeCase && (
              <div className="flex items-center gap-2 ml-2 pl-3 border-l border-slate-800">
                <span className="text-[10px] text-slate-400">Case ID:</span>
                <span className="text-[10px] font-mono font-bold text-blue-300 bg-blue-500/15 border border-blue-500/30 px-2 py-0.5 rounded">
                  {activeCase.case_id}
                </span>
                {lastEvaluation?.is_anomaly && (
                  <span className="flex items-center gap-1 text-[9.5px] font-bold text-rose-300 bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 rounded animate-pulse">
                    <ShieldAlert size={11} /> ANOMALY DETECTED
                  </span>
                )}
              </div>
            )}
          </div>

          <HealthIndicator
            status={status}
            health={health}
            onRefresh={refreshHealth}
          />
        </header>

        {/* Content Body */}
        <div className="flex-1 flex overflow-hidden">
          {activeTab === 'simulator' ? (
            <>
              {/* Left Canvas: React Flow Graph */}
              <div className="flex-1 p-3 overflow-hidden">
                <WorkflowCanvas
                  workflow={selectedWorkflow}
                  currentState={activeCase?.current_state_key}
                  visitedStates={visitedStates}
                  highlightedTransition={highlightedTransition}
                />
              </div>

              {/* Right Panel: Simulator Driver + Anomaly Inspector */}
              <div className="w-[430px] border-l border-slate-800/80 bg-slate-950/60 flex flex-col overflow-hidden shrink-0 shadow-2xl backdrop-blur-xl">
                <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
                  <EventSimulator
                    workflow={selectedWorkflow}
                    activeCase={activeCase}
                    loading={caseLoading}
                    error={caseError}
                    eventHistory={eventHistory}
                    onCreateCase={handleCreateCase}
                    onSendEvent={sendEvent}
                    onRunScenario={runScenario}
                    onClearCase={clearCase}
                  />

                  {/* Anomaly Inspection Card */}
                  <div className="border-t border-slate-800/80 pt-3.5">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-bold text-slate-200">
                        Hybrid Verification Matrix
                      </h3>
                      <span className="text-[9.5px] text-slate-500 font-mono">
                        DFA ⊕ Isolation Forest
                      </span>
                    </div>
                    <AnomalyInspector evaluation={lastEvaluation} />
                  </div>
                </div>
              </div>
            </>
          ) : activeTab === 'anomalies' ? (
            <div className="flex-1 p-5 overflow-y-auto">
              <AnomalyHistory />
            </div>
          ) : activeTab === 'batch' ? (
            <div className="flex-1 p-5 overflow-y-auto">
              <BatchSimulator />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default App;
