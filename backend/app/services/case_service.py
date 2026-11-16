"""Case management service: case lifecycle, event execution, and persistence."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.engine.hybrid_engine import HybridClassification, HybridEngine
from app.models.anomaly import AnomalyResult, AnomalySeverityEnum, DetectorTypeEnum
from app.models.case import CaseStatusEnum, ProcessCase
from app.models.event import EventLog
from app.models.workflow import Workflow, WorkflowState
from app.schemas.case import CaseCreateRequest
from app.schemas.event import EventSubmitRequest
from app.services.workflow_service import WorkflowService


class CaseService:
    """Business logic for process cases, event ingestion, and anomaly recording."""

    @staticmethod
    def create_case(session: Session, request: CaseCreateRequest) -> ProcessCase:
        """Create a new process case starting at the workflow's initial state."""
        workflow = WorkflowService.get_workflow_by_id_or_code(session, request.workflow_code)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{request.workflow_code}' not found.",
            )

        # Identify the initial state q0
        initial_state = next((s for s in workflow.states if s.is_initial), None)
        if not initial_state:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow '{workflow.code}' has no initial state configured.",
            )

        case_id = request.case_id or f"CASE-{uuid.uuid4().hex[:10].upper()}"

        # Check for existing case ID
        existing = session.execute(
            select(ProcessCase).where(ProcessCase.case_id == case_id)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case with ID '{case_id}' already exists.",
            )

        new_case = ProcessCase(
            case_id=case_id,
            workflow_id=workflow.id,
            current_state_id=initial_state.id,
            status=CaseStatusEnum.RUNNING,
            total_amount=request.total_amount,
            user_id=request.user_id,
            retry_count=0,
            metadata_json=request.metadata_json or {},
        )
        session.add(new_case)
        session.commit()
        session.refresh(new_case)
        return new_case

    @staticmethod
    def get_case(session: Session, case_id: str) -> ProcessCase:
        """Retrieve a process case by case_id along with events, states, and anomalies."""
        stmt = (
            select(ProcessCase)
            .where(ProcessCase.case_id == case_id)
            .options(
                selectinload(ProcessCase.workflow).selectinload(Workflow.states),
                selectinload(ProcessCase.current_state),
                selectinload(ProcessCase.events),
                selectinload(ProcessCase.anomalies),
            )
        )
        case = session.execute(stmt).scalar_one_or_none()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{case_id}' not found.",
            )
        return case

    @classmethod
    def submit_event(
        cls,
        session: Session,
        case_id: str,
        request: EventSubmitRequest,
        hybrid_engine: Optional[HybridEngine] = None,
    ) -> Dict[str, Any]:
        """Process an event transition for a case, update state, and perform hybrid evaluation."""
        case = cls.get_case(session, case_id)

        # Idempotency check: if an idempotency key was supplied and matches last event
        if request.idempotency_key and case.events:
            last_ev = case.events[-1]
            if last_ev.payload_json and last_ev.payload_json.get("idempotency_key") == request.idempotency_key:
                # Return existing event result without duplicate processing
                return {
                    "case_id": case.case_id,
                    "current_state": case.current_state.state_key,
                    "status": case.status.value,
                    "event": last_ev,
                    "evaluation": {"idempotent_replay": True, "message": "Duplicate event submission prevented."},
                }

        workflow = case.workflow
        state_map = {s.state_key: s for s in workflow.states}
        from_state_key = case.current_state.state_key

        # Prepare hybrid engine
        engine = hybrid_engine or HybridEngine.default()
        dfa_engine = engine.dfa_engine

        # 1. Execute single step on DFA
        step_res = dfa_engine.step(
            current_state=from_state_key,
            event=request.event_name,
            retry_count=case.retry_count,
        )

        to_state_key = step_res.to_state
        to_state_obj = state_map.get(to_state_key)

        # If to_state is TRAP_STATE and not in state_map, fall back or create
        if not to_state_obj:
            to_state_obj = state_map.get("TRAP_STATE")
            if not to_state_obj:
                to_state_obj = case.current_state

        # 2. Append EventLog
        payload = dict(request.payload_json or {})
        if request.idempotency_key:
            payload["idempotency_key"] = request.idempotency_key

        event_log = EventLog(
            case_id=case.case_id,
            workflow_id=workflow.id,
            event_name=request.event_name,
            from_state_key=from_state_key,
            to_state_key=to_state_key,
            execution_duration_ms=request.execution_duration_ms or 0,
            retry_count=case.retry_count,
            payload_json=payload,
        )
        session.add(event_log)
        session.flush()  # Generate event_log.id

        # 3. Update Case State & Retries
        case.current_state_id = to_state_obj.id
        case.retry_count = step_res.next_retry_count

        # Check terminal conditions
        if to_state_obj.is_terminal:
            if to_state_obj.state_type.value == "TERMINAL_SUCCESS":
                case.status = CaseStatusEnum.COMPLETED
            elif to_state_obj.state_type.value == "ERROR":
                case.status = CaseStatusEnum.ANOMALOUS
            else:
                case.status = CaseStatusEnum.FAILED
            case.completed_at = datetime.now(timezone.utc)
        elif not step_res.is_valid:
            case.status = CaseStatusEnum.ANOMALOUS

        # 4. Re-evaluate complete trace with Hybrid Engine
        all_events_data = [
            {
                "event_name": ev.event_name,
                "from_state": ev.from_state_key,
                "to_state": ev.to_state_key,
                "execution_duration_ms": ev.execution_duration_ms,
                "timestamp": ev.timestamp.isoformat(),
            }
            for ev in case.events
        ] + [{
            "event_name": event_log.event_name,
            "from_state": event_log.from_state_key,
            "to_state": event_log.to_state_key,
            "execution_duration_ms": event_log.execution_duration_ms,
            "timestamp": event_log.timestamp.isoformat() if event_log.timestamp else datetime.now(timezone.utc).isoformat(),
        }]

        trace_data = {
            "case_id": case.case_id,
            "total_amount": float(case.total_amount or 0.0),
            "retry_count": case.retry_count,
            "events": all_events_data,
        }

        eval_result = engine.evaluate_case(trace_data)

        # 5. Record AnomalyResult if an anomaly is detected
        if eval_result.is_anomaly:
            case.status = CaseStatusEnum.ANOMALOUS
            detector_type = DetectorTypeEnum.HYBRID
            if eval_result.classification == HybridClassification.SYNTACTIC_ANOMALY:
                detector_type = DetectorTypeEnum.DFA
            elif eval_result.classification == HybridClassification.BEHAVIORAL_ANOMALY:
                detector_type = DetectorTypeEnum.ISOLATION_FOREST

            anomaly_record = AnomalyResult(
                case_id=case.case_id,
                event_log_id=event_log.id,
                detector_type=detector_type,
                is_anomaly=True,
                anomaly_score=eval_result.ml_score if eval_result.ml_score > 0 else None,
                anomaly_reason=eval_result.explanation[:250],
                severity=eval_result.severity,
                rule_violation=eval_result.dfa_error_type.value if eval_result.dfa_error_type else None,
                details_json=eval_result.to_dict(),
            )
            session.add(anomaly_record)

        session.commit()
        session.refresh(case)
        session.refresh(event_log)

        return {
            "case_id": case.case_id,
            "current_state": to_state_key,
            "status": case.status.value,
            "event": event_log,
            "evaluation": eval_result.to_dict(),
        }

    @staticmethod
    def get_anomalies(
        session: Session,
        page: int = 1,
        page_size: int = 20,
        case_id: Optional[str] = None,
        severity: Optional[str] = None,
        detector_type: Optional[str] = None,
    ) -> Tuple[List[AnomalyResult], int]:
        """Fetch paginated anomaly records with optional filters."""
        stmt = select(AnomalyResult)

        if case_id:
            stmt = stmt.where(AnomalyResult.case_id == case_id)
        if severity:
            stmt = stmt.where(AnomalyResult.severity == severity)
        if detector_type:
            stmt = stmt.where(AnomalyResult.detector_type == detector_type)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(total_stmt).scalar() or 0

        stmt = stmt.order_by(AnomalyResult.id.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(session.execute(stmt).scalars().all())

        return items, total
