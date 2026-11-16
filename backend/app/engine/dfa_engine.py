"""Theory of Computation (TOC) Core: Deterministic Finite Automaton (DFA) Engine.

Represents a formal 5-tuple automaton M = (Q, Sigma, delta, q0, F) with support
for bounded execution context (retry counters) and comprehensive trace
validation.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DFAErrorType(str, Enum):
    """Classification of automaton rejection reasons."""

    UNKNOWN_EVENT = "UNKNOWN_EVENT"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    RETRY_LIMIT_EXCEEDED = "RETRY_LIMIT_EXCEEDED"
    GUARD_CONDITION_FAILED = "GUARD_CONDITION_FAILED"
    TERMINAL_STATE_VIOLATION = "TERMINAL_STATE_VIOLATION"
    MALFORMED_DEFINITION = "MALFORMED_DEFINITION"


class WorkflowDefinitionError(Exception):
    """Raised when an automaton definition violates DFA formal requirements."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]


@dataclass(frozen=True)
class DFAState:
    """Formal state q in set of states Q."""

    key: str
    name: str
    state_type: str = "INTERMEDIATE"  # START, INTERMEDIATE, TERMINAL_SUCCESS, TERMINAL_FAILURE, ERROR
    is_initial: bool = False
    is_terminal: bool = False
    description: Optional[str] = None


@dataclass(frozen=True)
class DFATransition:
    """Transition delta(from_state, event) -> to_state with guard rules."""

    from_state: str
    event: str
    to_state: str
    is_allowed: bool = True
    max_retries: int = 0
    condition_meta: Optional[Dict[str, Any]] = None


@dataclass
class TransitionResult:
    """Outcome of stepping the automaton with an input event."""

    is_valid: bool
    from_state: str
    event: str
    to_state: str
    next_retry_count: int
    error_type: Optional[DFAErrorType] = None
    error_message: Optional[str] = None


@dataclass
class TraceValidationResult:
    """Comprehensive validation result for an event sequence."""

    is_valid: bool
    is_completed: bool
    is_partial: bool
    visited_states: List[str]
    events: List[str]
    final_state: str
    final_retry_count: int
    first_invalid_index: Optional[int] = None
    first_invalid_event: Optional[str] = None
    first_invalid_state: Optional[str] = None
    error_type: Optional[DFAErrorType] = None
    error_message: Optional[str] = None
    transition_history: List[TransitionResult] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable evaluation summary."""
        if self.is_valid:
            status = "COMPLETED" if self.is_completed else "IN_PROGRESS (PARTIAL)"
            return f"VALID [{status}]: Path: {' -> '.join(self.visited_states)}"
        return (
            f"INVALID [{self.error_type}]: Failed at step {self.first_invalid_index} "
            f"on event '{self.first_invalid_event}' from state '{self.first_invalid_state}'. "
            f"Reason: {self.error_message}"
        )


class DFAEngine:
    """Deterministic Finite Automaton (DFA) Workflow Engine.

    Formal Automaton Definition:
        M = (Q, Sigma, delta, q0, F)
        - Q: Finite set of states
        - Sigma: Alphabet of valid input events
        - delta: Transition function Q x Sigma -> Q
        - q0: Initial state (q0 in Q)
        - F: Set of accepting/terminal states (F subset of Q)

    Bounded Retry Handling:
        An ordinary DFA cannot enforce arbitrary unbounded counters without
        violating the finite-state property. However, since the retry limit K
        is finite (e.g. K = 3), this engine models bounded retries as an
        Extended Finite State Machine (EFSM) with state space Q x {0, ..., K},
        which is mathematically isomorphic to an expanded pure DFA with
        |Q| x (K + 1) states.

    Trap State:
        Any undefined or disallowed transition immediately leads to TRAP_STATE,
        halting valid process execution and preserving violation diagnostics.
    """

    TRAP_STATE = "TRAP_STATE"

    def __init__(
        self,
        states: Dict[str, DFAState],
        alphabet: Set[str],
        initial_state: str,
        transitions: Dict[Tuple[str, str], DFATransition],
        accepting_states: Set[str],
        workflow_code: str = "WORKFLOW",
        workflow_name: str = "Workflow",
        validate_on_init: bool = True,
    ):
        self.states = states
        self.alphabet = set(alphabet)
        self.initial_state = initial_state
        self.transitions = transitions
        self.accepting_states = set(accepting_states)
        self.workflow_code = workflow_code
        self.workflow_name = workflow_name

        if validate_on_init:
            errors = self.validate_definition()
            if errors:
                raise WorkflowDefinitionError(
                    f"Invalid DFA definition for workflow '{workflow_code}': {'; '.join(errors)}",
                    errors=errors,
                )

    # ------------------------------------------------------------------
    # Definition Validation & Graph Analysis
    # ------------------------------------------------------------------

    def validate_definition(self) -> List[str]:
        """Verify formal DFA integrity constraints.

        Checks:
        1. Initial state exists in Q.
        2. Accepting states F are a subset of Q.
        3. All transitions reference valid states in Q.
        4. Transition symbols belong to the alphabet Sigma.
        5. Trap state exists or can be targeted safely.
        """
        errors: List[str] = []

        if not self.initial_state:
            errors.append("Initial state q0 is not defined.")
        elif self.initial_state not in self.states:
            errors.append(f"Initial state '{self.initial_state}' is not in states Q.")

        for f_state in self.accepting_states:
            if f_state not in self.states:
                errors.append(f"Accepting state '{f_state}' is not in states Q.")

        for (from_s, event), trans in self.transitions.items():
            if from_s not in self.states:
                errors.append(f"Transition from_state '{from_s}' is not in states Q.")
            if trans.to_state not in self.states and trans.to_state != self.TRAP_STATE:
                errors.append(f"Transition to_state '{trans.to_state}' is not in states Q.")
            if event not in self.alphabet:
                errors.append(f"Transition event '{event}' is not in alphabet Sigma.")

        return errors

    def get_reachable_states(self) -> Set[str]:
        """Compute all states reachable from q0 using Breadth-First Search (BFS)."""
        if self.initial_state not in self.states:
            return set()

        visited: Set[str] = {self.initial_state}
        queue = deque([self.initial_state])

        # Precompute adjacency list
        adj: Dict[str, Set[str]] = {s: set() for s in self.states}
        for (from_s, _), trans in self.transitions.items():
            if trans.is_allowed and from_s in adj:
                adj[from_s].add(trans.to_state)

        while queue:
            curr = queue.popleft()
            for neighbor in adj.get(curr, set()):
                if neighbor in self.states and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited

    def get_unreachable_states(self) -> Set[str]:
        """Return states defined in Q that cannot be reached from initial state q0."""
        return set(self.states.keys()) - self.get_reachable_states()

    def get_dead_end_states(self) -> Set[str]:
        """Identify non-terminal states that have no valid outgoing transitions."""
        states_with_outgoing: Set[str] = set()
        for (from_s, _), trans in self.transitions.items():
            if trans.is_allowed:
                states_with_outgoing.add(from_s)

        dead_ends: Set[str] = set()
        for key, state in self.states.items():
            if not state.is_terminal and key not in states_with_outgoing:
                dead_ends.add(key)
        return dead_ends

    # ------------------------------------------------------------------
    # Core Transition Step Function
    # ------------------------------------------------------------------

    def step(
        self,
        current_state: str,
        event: str,
        retry_count: int = 0,
    ) -> TransitionResult:
        """Execute a single transition delta(current_state, event) -> next_state.

        Evaluates syntax, retry bounds, guard conditions, and terminal states.
        On any rejection, transitions deterministically to TRAP_STATE while
        recording the exact failure reason.
        """
        # 1. Unknown event symbol (not in alphabet Sigma)
        if event not in self.alphabet:
            return TransitionResult(
                is_valid=False,
                from_state=current_state,
                event=event,
                to_state=self.TRAP_STATE,
                next_retry_count=retry_count,
                error_type=DFAErrorType.UNKNOWN_EVENT,
                error_message=f"Event '{event}' is not in the recognized alphabet Sigma.",
            )

        # 2. Unknown current state
        state_obj = self.states.get(current_state)
        if not state_obj:
            return TransitionResult(
                is_valid=False,
                from_state=current_state,
                event=event,
                to_state=self.TRAP_STATE,
                next_retry_count=retry_count,
                error_type=DFAErrorType.ILLEGAL_TRANSITION,
                error_message=f"Current state '{current_state}' is not defined in Q.",
            )

        # 3. Terminal state invariant: No transitions allowed out of terminal states
        if state_obj.is_terminal:
            return TransitionResult(
                is_valid=False,
                from_state=current_state,
                event=event,
                to_state=self.TRAP_STATE,
                next_retry_count=retry_count,
                error_type=DFAErrorType.TERMINAL_STATE_VIOLATION,
                error_message=(
                    f"State '{current_state}' is terminal ({state_obj.state_type}). "
                    f"No further transitions are permitted."
                ),
            )

        # 4. Lookup transition in delta
        trans = self.transitions.get((current_state, event))
        if not trans or not trans.is_allowed:
            return TransitionResult(
                is_valid=False,
                from_state=current_state,
                event=event,
                to_state=self.TRAP_STATE,
                next_retry_count=retry_count,
                error_type=DFAErrorType.ILLEGAL_TRANSITION,
                error_message=(
                    f"Transition delta('{current_state}', '{event}') is not permitted."
                ),
            )

        # 5. Evaluate guard conditions & bounded retry rules
        next_retries = retry_count

        # Case A: Retry trigger (e.g. RETRY_PAYMENT)
        if event == "RETRY_PAYMENT" or (trans.condition_meta and "retry_limit" in trans.condition_meta):
            limit = trans.max_retries or (trans.condition_meta.get("max_retries", 3) if trans.condition_meta else 3)
            if retry_count >= limit:
                return TransitionResult(
                    is_valid=False,
                    from_state=current_state,
                    event=event,
                    to_state=self.TRAP_STATE,
                    next_retry_count=retry_count,
                    error_type=DFAErrorType.RETRY_LIMIT_EXCEEDED,
                    error_message=(
                        f"Maximum retry limit ({limit}) exceeded. "
                        f"Current retry count is {retry_count}."
                    ),
                )
            next_retries = retry_count + 1

        # Case B: Exceed max retries trigger (e.g. EXCEED_MAX_RETRIES)
        elif event == "EXCEED_MAX_RETRIES":
            limit = trans.max_retries or (trans.condition_meta.get("max_retries", 3) if trans.condition_meta else 3)
            if retry_count < limit:
                return TransitionResult(
                    is_valid=False,
                    from_state=current_state,
                    event=event,
                    to_state=self.TRAP_STATE,
                    next_retry_count=retry_count,
                    error_type=DFAErrorType.GUARD_CONDITION_FAILED,
                    error_message=(
                        f"Cannot trigger EXCEED_MAX_RETRIES when retries have not been exhausted. "
                        f"Current retry count: {retry_count}, required: >= {limit}."
                    ),
                )

        # Valid transition accepted
        return TransitionResult(
            is_valid=True,
            from_state=current_state,
            event=event,
            to_state=trans.to_state,
            next_retry_count=next_retries,
        )

    # ------------------------------------------------------------------
    # Trace Validation
    # ------------------------------------------------------------------

    def validate_trace(
        self,
        events: List[str],
        initial_state: Optional[str] = None,
        initial_retry_count: int = 0,
    ) -> TraceValidationResult:
        """Validate an entire sequence of input events w in Sigma*.

        Distinguishes:
        - VALID & COMPLETED: Trace ends in an accepting terminal state F.
        - VALID & PARTIAL: Intermediate valid execution that has not yet reached F.
        - INVALID: Trace violates transition delta, retry bounds, or alphabet.
        """
        curr_state = initial_state or self.initial_state
        curr_retries = initial_retry_count
        visited_states = [curr_state]
        history: List[TransitionResult] = []

        # Empty event trace: valid initial or partial state
        if not events:
            is_term = curr_state in self.accepting_states
            return TraceValidationResult(
                is_valid=True,
                is_completed=is_term,
                is_partial=not is_term,
                visited_states=visited_states,
                events=[],
                final_state=curr_state,
                final_retry_count=curr_retries,
                transition_history=[],
            )

        # Iterate through events step-by-step
        for idx, event in enumerate(events):
            result = self.step(curr_state, event, curr_retries)
            history.append(result)

            if not result.is_valid:
                # Transition to TRAP_STATE
                visited_states.append(result.to_state)
                return TraceValidationResult(
                    is_valid=False,
                    is_completed=False,
                    is_partial=False,
                    visited_states=visited_states,
                    events=events[: idx + 1],
                    final_state=result.to_state,
                    final_retry_count=curr_retries,
                    first_invalid_index=idx,
                    first_invalid_event=event,
                    first_invalid_state=curr_state,
                    error_type=result.error_type,
                    error_message=result.error_message,
                    transition_history=history,
                )

            curr_state = result.to_state
            curr_retries = result.next_retry_count
            visited_states.append(curr_state)

        # Trace succeeded
        is_completed = curr_state in self.accepting_states
        return TraceValidationResult(
            is_valid=True,
            is_completed=is_completed,
            is_partial=not is_completed,
            visited_states=visited_states,
            events=events,
            final_state=curr_state,
            final_retry_count=curr_retries,
            transition_history=history,
        )

    # ------------------------------------------------------------------
    # Factory Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DFAEngine":
        """Build DFAEngine from an in-memory dictionary definition."""
        states = {
            s["key"]: DFAState(
                key=s["key"],
                name=s.get("name", s["key"]),
                state_type=s.get("state_type", "INTERMEDIATE"),
                is_initial=s.get("is_initial", False),
                is_terminal=s.get("is_terminal", False),
                description=s.get("description"),
            )
            for s in data["states"]
        }

        alphabet = set(data["alphabet"])
        initial_state = data["initial_state"]
        accepting_states = set(data.get("accepting_states", []))

        transitions: Dict[Tuple[str, str], DFATransition] = {}
        for t in data["transitions"]:
            transitions[(t["from_state"], t["event"])] = DFATransition(
                from_state=t["from_state"],
                event=t["event"],
                to_state=t["to_state"],
                is_allowed=t.get("is_allowed", True),
                max_retries=t.get("max_retries", 0),
                condition_meta=t.get("condition_meta"),
            )

        return cls(
            states=states,
            alphabet=alphabet,
            initial_state=initial_state,
            transitions=transitions,
            accepting_states=accepting_states,
            workflow_code=data.get("workflow_code", "CUSTOM_WORKFLOW"),
            workflow_name=data.get("workflow_name", "Custom Workflow"),
        )

    @classmethod
    def from_db_workflow(cls, workflow: Any) -> "DFAEngine":
        """Construct a DFAEngine directly from a SQLAlchemy Workflow ORM instance.

        Decouples ORM extraction from DFA logic so no active DB session is
        held during transition evaluations.
        """
        # Map states by state_key
        state_id_to_key: Dict[int, str] = {}
        states: Dict[str, DFAState] = {}
        initial_state: Optional[str] = None
        accepting_states: Set[str] = set()
        alphabet: Set[str] = set()

        for s in workflow.states:
            state_id_to_key[s.id] = s.state_key
            stype = s.state_type.value if hasattr(s.state_type, "value") else str(s.state_type)
            state_obj = DFAState(
                key=s.state_key,
                name=s.state_name,
                state_type=stype,
                is_initial=s.is_initial,
                is_terminal=s.is_terminal,
                description=s.description,
            )
            states[s.state_key] = state_obj
            if s.is_initial:
                initial_state = s.state_key
            if s.is_terminal:
                accepting_states.add(s.state_key)

        transitions: Dict[Tuple[str, str], DFATransition] = {}
        for t in workflow.transitions:
            from_key = state_id_to_key.get(t.from_state_id)
            to_key = state_id_to_key.get(t.to_state_id)
            if from_key and to_key:
                transitions[(from_key, t.event_name)] = DFATransition(
                    from_state=from_key,
                    event=t.event_name,
                    to_state=to_key,
                    is_allowed=t.is_allowed,
                    max_retries=t.max_retries,
                    condition_meta=t.condition_meta,
                )
                alphabet.add(t.event_name)

        if not initial_state:
            raise WorkflowDefinitionError(
                f"Workflow '{workflow.code}' has no state designated with is_initial=True."
            )

        return cls(
            states=states,
            alphabet=alphabet,
            initial_state=initial_state,
            transitions=transitions,
            accepting_states=accepting_states,
            workflow_code=workflow.code,
            workflow_name=workflow.name,
        )


def get_online_payment_dfa() -> DFAEngine:
    """Return an in-memory DFAEngine for Online Payment Processing matching schema.sql."""
    return DFAEngine.from_dict({
        "workflow_code": "ONLINE_PAYMENT",
        "workflow_name": "Online Payment Processing Workflow",
        "initial_state": "ORDER_CREATED",
        "accepting_states": ["ORDER_CONFIRMED", "ORDER_CANCELLED"],
        "states": [
            {
                "key": "ORDER_CREATED",
                "name": "Order Created",
                "state_type": "START",
                "is_initial": True,
                "is_terminal": False,
            },
            {
                "key": "PAYMENT_INITIATED",
                "name": "Payment Initiated",
                "state_type": "INTERMEDIATE",
                "is_initial": False,
                "is_terminal": False,
            },
            {
                "key": "PAYMENT_VERIFYING",
                "name": "Payment Verifying",
                "state_type": "INTERMEDIATE",
                "is_initial": False,
                "is_terminal": False,
            },
            {
                "key": "PAYMENT_FAILED",
                "name": "Payment Failed",
                "state_type": "INTERMEDIATE",
                "is_initial": False,
                "is_terminal": False,
            },
            {
                "key": "ORDER_CONFIRMED",
                "name": "Order Confirmed",
                "state_type": "TERMINAL_SUCCESS",
                "is_initial": False,
                "is_terminal": True,
            },
            {
                "key": "ORDER_CANCELLED",
                "name": "Order Cancelled",
                "state_type": "TERMINAL_FAILURE",
                "is_initial": False,
                "is_terminal": True,
            },
            {
                "key": "TRAP_STATE",
                "name": "Trap / Reject State",
                "state_type": "ERROR",
                "is_initial": False,
                "is_terminal": True,
            },
        ],
        "alphabet": [
            "INITIATE_PAYMENT",
            "CANCEL_ORDER",
            "VERIFY_PAYMENT",
            "PAYMENT_SUCCESS",
            "PAYMENT_FAILURE",
            "RETRY_PAYMENT",
            "EXCEED_MAX_RETRIES",
        ],
        "transitions": [
            {
                "from_state": "ORDER_CREATED",
                "event": "INITIATE_PAYMENT",
                "to_state": "PAYMENT_INITIATED",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "ORDER_CREATED",
                "event": "CANCEL_ORDER",
                "to_state": "ORDER_CANCELLED",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "PAYMENT_INITIATED",
                "event": "VERIFY_PAYMENT",
                "to_state": "PAYMENT_VERIFYING",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "PAYMENT_INITIATED",
                "event": "CANCEL_ORDER",
                "to_state": "ORDER_CANCELLED",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "PAYMENT_VERIFYING",
                "event": "PAYMENT_SUCCESS",
                "to_state": "ORDER_CONFIRMED",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "PAYMENT_VERIFYING",
                "event": "PAYMENT_FAILURE",
                "to_state": "PAYMENT_FAILED",
                "is_allowed": True,
                "max_retries": 0,
            },
            {
                "from_state": "PAYMENT_FAILED",
                "event": "RETRY_PAYMENT",
                "to_state": "PAYMENT_INITIATED",
                "is_allowed": True,
                "max_retries": 3,
                "condition_meta": {"max_retries": 3, "rule": "retry_count < 3"},
            },
            {
                "from_state": "PAYMENT_FAILED",
                "event": "EXCEED_MAX_RETRIES",
                "to_state": "ORDER_CANCELLED",
                "is_allowed": True,
                "max_retries": 3,
                "condition_meta": {"max_retries": 3, "rule": "retry_count >= 3"},
            },
            {
                "from_state": "PAYMENT_FAILED",
                "event": "CANCEL_ORDER",
                "to_state": "ORDER_CANCELLED",
                "is_allowed": True,
                "max_retries": 0,
            },
        ],
    })
