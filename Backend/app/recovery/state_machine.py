"""Recovery status state machine.

Recovery.status transitions are mostly driven directly by the LangGraph
agent (see app/agent/graph.py and the nodes it calls), but pause/resume
and any future manual controls should route through here so illegal
transitions are caught in one place.
"""

# status -> set of statuses it may legally transition to
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"analyzing", "paused", "cancelled"},
    "analyzing": {"executing", "recovered", "exhausted", "escalated", "unsafe_to_retry", "paused"},
    "executing": {"observing", "adapting", "recovered", "exhausted", "escalated", "unsafe_to_retry"},
    "observing": {"adapting", "recovered", "exhausted", "paused", "escalated"},
    "adapting": {"executing", "recovered", "exhausted", "escalated", "unsafe_to_retry"},
    "paused": {"pending"},
    "escalated": {"pending", "analyzing", "executing", "exhausted", "cancelled", "recovered"},
    "recovered": set(),
    "exhausted": set(),
    "unsafe_to_retry": set(),
    "cancelled": set(),
}

TERMINAL_STATUSES = {"recovered", "exhausted", "unsafe_to_retry", "cancelled"}


def can_transition(current: str, target: str) -> bool:
    """Whether moving a Recovery from `current` to `target` status is legal."""
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, set())


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
