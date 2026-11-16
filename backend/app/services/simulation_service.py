"""Simulation service for batch evaluation of process traces."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.engine.hybrid_engine import HybridClassification, HybridEngine
from app.schemas.simulation import (
    BatchSimulationRequest,
    BatchSimulationResponse,
    SimulationCaseResult,
)
from app.services.workflow_service import WorkflowService


class SimulationService:
    """Handles batch simulation requests against the Hybrid Engine."""

    @staticmethod
    def run_batch_simulation(
        session: Session,
        request: BatchSimulationRequest,
        hybrid_engine: Optional[HybridEngine] = None,
    ) -> BatchSimulationResponse:
        """Evaluate a batch of simulated execution traces."""
        workflow = WorkflowService.get_workflow_by_id_or_code(session, request.workflow_code)
        engine = hybrid_engine or HybridEngine.default()

        if workflow and workflow.code != engine.dfa_engine.workflow_code:
            dfa = WorkflowService.get_dfa_for_workflow(workflow)
            engine = HybridEngine(dfa_engine=dfa, ml_engine=engine.ml_engine)

        results: List[SimulationCaseResult] = []
        normal_count = 0
        syntactic_count = 0
        behavioral_count = 0
        compound_count = 0

        for case_input in request.cases:
            try:
                events_list = [
                    {
                        "event_name": ev.event_name,
                        "execution_duration_ms": ev.execution_duration_ms or 0,
                        "inter_event_delay_ms": ev.inter_event_delay_ms or 0,
                        "payload": ev.payload or {},
                    }
                    for ev in case_input.events
                ]

                case_dict = {
                    "case_id": case_input.case_id,
                    "total_amount": float(case_input.total_amount or 0.0),
                    "user_id": case_input.user_id,
                    "events": events_list,
                }

                eval_res = engine.evaluate_case(case_dict)

                if eval_res.classification == HybridClassification.NORMAL:
                    normal_count += 1
                elif eval_res.classification == HybridClassification.SYNTACTIC_ANOMALY:
                    syntactic_count += 1
                elif eval_res.classification == HybridClassification.BEHAVIORAL_ANOMALY:
                    behavioral_count += 1
                elif eval_res.classification == HybridClassification.COMPOUND_ANOMALY:
                    compound_count += 1

                results.append(
                    SimulationCaseResult(
                        case_id=case_input.case_id,
                        is_anomaly=eval_res.is_anomaly,
                        classification=eval_res.classification.value,
                        severity=eval_res.severity.value,
                        final_state=eval_res.final_state,
                        explanation=eval_res.explanation,
                        evaluation=eval_res.to_dict(),
                    )
                )
            except Exception as exc:
                results.append(
                    SimulationCaseResult(
                        case_id=case_input.case_id,
                        is_anomaly=True,
                        classification="ERROR",
                        severity="HIGH",
                        final_state="UNKNOWN",
                        explanation=f"Evaluation failed: {str(exc)}",
                        evaluation={},
                        error=str(exc),
                    )
                )

        total_anomalies = syntactic_count + behavioral_count + compound_count

        return BatchSimulationResponse(
            workflow_code=request.workflow_code,
            total_cases=len(request.cases),
            processed_count=len(results),
            anomalies_detected=total_anomalies,
            normal_count=normal_count,
            syntactic_anomalies=syntactic_count,
            behavioral_anomalies=behavioral_count,
            compound_anomalies=compound_count,
            results=results,
        )
