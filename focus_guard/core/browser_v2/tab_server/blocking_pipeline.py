"""Modular blocking pipeline for auditable URL blocking decisions.

Implements a step-based pipeline: each step returns a BlockingStepResult.
The first step that returns a terminal result determines the final decision.
All steps and the winning outcome are recorded in a step_trace for auditing.

See: docs/planning/wip/PROJECT_PLAN_TODO/TODOs/cursor/BLOCKING_CLASSIFICATION_PRIORITY_AND_DESIGN.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .blocking import BlockingDecision, BlockingRule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BlockingRequest:
    """Immutable input for one blocking check."""

    url: str
    domain: str
    title: str = ""
    tab_id: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockingStepResult:
    """Result of one pipeline step."""

    terminal: bool
    """If True, pipeline stops and this step's outcome is the final decision."""

    should_block: bool
    reason: Optional[str] = None
    step_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    """Step-specific data: rule, classification, budget_status, category, etc."""


class BlockingContext:
    """Mutable bag shared across pipeline steps.

    Steps can read/write shared data (e.g. classification result, budget_status,
    search_check) so later steps avoid re-doing work.
    """

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data


# Step type: (request, context) -> Optional[BlockingStepResult]
# Return None to continue to the next step.
BlockingStep = Callable[[BlockingRequest, BlockingContext], Optional[BlockingStepResult]]


# One entry in the audit trace
@dataclass
class StepTraceEntry:
    """Single entry in the step trace for auditing."""

    step_name: str
    terminal: bool
    should_block: bool
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


def _step_result_to_decision(result: BlockingStepResult) -> BlockingDecision:
    """Build a BlockingDecision from a terminal BlockingStepResult."""
    rule = result.details.get("rule")
    classification = result.details.get("classification")
    budget_status = result.details.get("budget_status")
    return BlockingDecision(
        should_block=result.should_block,
        reason=result.reason,
        rule=rule,
        classification=classification,
        budget_status=budget_status,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class BlockingPipeline:
    """Ordered list of steps. First step that returns a terminal result wins."""

    def __init__(self) -> None:
        self._steps: List[Tuple[str, BlockingStep]] = []
        self._default_allow = True  # when no step returns terminal

    def add_step(self, name: str, step: BlockingStep) -> "BlockingPipeline":
        """Register a step with a name (for audit). Appended to the end."""
        self._steps.append((name, step))
        return self

    def run(
        self,
        request: BlockingRequest,
        context_initializer: Optional[
            Callable[[BlockingRequest], BlockingContext]
        ] = None,
    ) -> Tuple[BlockingDecision, List[StepTraceEntry]]:
        """Run steps in order until one returns a terminal result.

        Args:
            request: The blocking request.
            context_initializer: Optional. If provided, called with request to
                produce the initial BlockingContext (e.g. to inject _blocker).
                Otherwise a fresh BlockingContext() is used.

        Returns:
            (final_decision, step_trace). step_trace includes every step that ran
            and the winning step's outcome for auditing.
        """
        if context_initializer is not None:
            ctx = context_initializer(request)
        else:
            ctx = BlockingContext()
        trace: List[StepTraceEntry] = []
        final_result: Optional[BlockingStepResult] = None

        for step_name, step_fn in self._steps:
            try:
                result = step_fn(request, ctx)
            except Exception as e:
                logger.warning("Pipeline step %s failed: %s", step_name, e)
                result = None

            if result is not None:
                # Normalize step_name on result for trace
                if not result.step_name:
                    result = BlockingStepResult(
                        terminal=result.terminal,
                        should_block=result.should_block,
                        reason=result.reason,
                        step_name=step_name,
                        details=result.details,
                    )
                trace.append(
                    StepTraceEntry(
                        step_name=result.step_name,
                        terminal=result.terminal,
                        should_block=result.should_block,
                        reason=result.reason,
                        details=dict(result.details),
                    )
                )
                if result.terminal:
                    final_result = result
                    break

        if final_result is not None:
            decision = _step_result_to_decision(final_result)
        else:
            decision = BlockingDecision(should_block=not self._default_allow)

        return (decision, trace)
