"""Unit tests for the blocking pipeline runner and step types."""

import pytest

from focus_guard.core.browser_v2.tab_server.blocking_pipeline import (
    BlockingRequest,
    BlockingStepResult,
    BlockingContext,
    BlockingPipeline,
    StepTraceEntry,
)
from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision, BlockingRule


# ---------------------------------------------------------------------------
# BlockingRequest
# ---------------------------------------------------------------------------

class TestBlockingRequest:
    def test_minimal(self):
        r = BlockingRequest(url="https://example.com/", domain="example.com")
        assert r.url == "https://example.com/"
        assert r.domain == "example.com"
        assert r.title == ""
        assert r.tab_id is None
        assert r.context == {}

    def test_full(self):
        r = BlockingRequest(
            url="https://a.b.com/path",
            domain="b.com",
            title="Page",
            tab_id=1,
            context={"search_context": "drive"},
        )
        assert r.title == "Page"
        assert r.tab_id == 1
        assert r.context["search_context"] == "drive"


# ---------------------------------------------------------------------------
# BlockingStepResult / StepTraceEntry
# ---------------------------------------------------------------------------

class TestBlockingStepResult:
    def test_terminal_block(self):
        res = BlockingStepResult(
            terminal=True,
            should_block=True,
            reason="blocked",
            step_name="test_step",
            details={"rule": None, "category": "ADULT"},
        )
        assert res.terminal is True
        assert res.should_block is True
        assert res.details["category"] == "ADULT"

    def test_non_terminal_continue(self):
        res = BlockingStepResult(
            terminal=False,
            should_block=False,
            step_name="classification",
            details={"category": "EDUCATION"},
        )
        assert res.terminal is False


# ---------------------------------------------------------------------------
# BlockingContext
# ---------------------------------------------------------------------------

class TestBlockingContext:
    def test_get_set(self):
        ctx = BlockingContext()
        assert ctx.get("x") is None
        assert ctx.get("x", 42) == 42
        ctx.set("x", 1)
        assert ctx.get("x") == 1
        assert "x" in ctx

    def test_contains(self):
        ctx = BlockingContext()
        ctx.set("a", 1)
        assert "a" in ctx
        assert "b" not in ctx


# ---------------------------------------------------------------------------
# BlockingPipeline runner
# ---------------------------------------------------------------------------

class TestBlockingPipelineRunner:
    def test_empty_pipeline_default_allow(self):
        pipeline = BlockingPipeline()
        req = BlockingRequest(url="https://example.com/", domain="example.com")
        decision, trace = pipeline.run(req)
        assert decision.should_block is False
        assert trace == []

    def test_first_step_terminal_wins(self):
        def step_allow(_req: BlockingRequest, _ctx: BlockingContext) -> BlockingStepResult:
            return BlockingStepResult(
                terminal=True,
                should_block=False,
                reason="allowed",
                step_name="allow_step",
                details={},
            )

        pipeline = BlockingPipeline()
        pipeline.add_step("allow", step_allow)
        pipeline.add_step("other", lambda r, c: BlockingStepResult(terminal=True, should_block=True, step_name="other"))
        req = BlockingRequest(url="https://x.com/", domain="x.com")
        decision, trace = pipeline.run(req)
        assert decision.should_block is False
        assert decision.reason == "allowed"
        assert len(trace) == 1
        assert trace[0].step_name == "allow_step"
        assert trace[0].terminal is True

    def test_second_step_terminal_when_first_returns_none(self):
        def step_continue(_req: BlockingRequest, _ctx: BlockingContext) -> None:
            return None

        def step_block(_req: BlockingRequest, _ctx: BlockingContext) -> BlockingStepResult:
            return BlockingStepResult(
                terminal=True,
                should_block=True,
                reason="blocked by rule",
                step_name="block_step",
                details={
                    "rule": BlockingRule(domain="bad.com", reason="blocked by rule", category="ADULT"),
                    "classification": {"category": "ADULT"},
                },
            )

        pipeline = BlockingPipeline()
        pipeline.add_step("continue", step_continue)
        pipeline.add_step("block", step_block)
        req = BlockingRequest(url="https://bad.com/", domain="bad.com")
        decision, trace = pipeline.run(req)
        assert decision.should_block is True
        assert decision.reason == "blocked by rule"
        assert decision.rule is not None
        assert decision.rule.domain == "bad.com"
        assert decision.classification["category"] == "ADULT"
        # First step returns None (no trace entry); second step returns terminal -> one trace entry
        assert len(trace) == 1
        assert trace[0].step_name == "block_step"
        assert trace[0].terminal is True

    def test_non_terminal_result_continues(self):
        def step_non_terminal(_req: BlockingRequest, ctx: BlockingContext) -> BlockingStepResult:
            ctx.set("classification", {"category": "EDUCATION"})
            return BlockingStepResult(
                terminal=False,
                should_block=False,
                step_name="classification",
                details={},
            )

        def step_policy(_req: BlockingRequest, ctx: BlockingContext) -> BlockingStepResult:
            cl = ctx.get("classification", {})
            return BlockingStepResult(
                terminal=True,
                should_block=cl.get("category") == "ADULT",
                reason="policy" if cl.get("category") == "ADULT" else None,
                step_name="policy",
                details={"classification": cl},
            )

        pipeline = BlockingPipeline()
        pipeline.add_step("classification", step_non_terminal)
        pipeline.add_step("policy", step_policy)
        req = BlockingRequest(url="https://edu.com/", domain="edu.com")
        decision, trace = pipeline.run(req)
        assert decision.should_block is False
        assert len(trace) == 2
        assert trace[0].step_name == "classification"
        assert trace[0].terminal is False
        assert trace[1].step_name == "policy"
        assert trace[1].terminal is True

    def test_step_exception_logged_pipeline_continues(self):
        def step_raises(_req: BlockingRequest, _ctx: BlockingContext) -> BlockingStepResult:
            raise ValueError("step failed")

        def step_allow(_req: BlockingRequest, _ctx: BlockingContext) -> BlockingStepResult:
            return BlockingStepResult(terminal=True, should_block=False, step_name="allow", details={})

        pipeline = BlockingPipeline()
        pipeline.add_step("bad", step_raises)
        pipeline.add_step("allow", step_allow)
        req = BlockingRequest(url="https://example.com/", domain="example.com")
        decision, trace = pipeline.run(req)
        # Exception is caught, result is None, so we continue; allow step runs
        assert decision.should_block is False
        assert len(trace) == 1
        assert trace[0].step_name == "allow"

    def test_step_trace_entry_details_copied(self):
        details = {"category": "GAMING", "nested": {"a": 1}}
        res = BlockingStepResult(
            terminal=True,
            should_block=True,
            reason="gaming",
            step_name="policy",
            details=details,
        )
        pipeline = BlockingPipeline()
        pipeline.add_step("one", lambda r, c: res)
        decision, trace = pipeline.run(BlockingRequest(url="https://g.com/", domain="g.com"))
        assert trace[0].details is not details
        assert trace[0].details == details

    def test_run_with_context_initializer(self):
        """Context initializer injects values that steps can read."""
        def step_use_ctx(_req: BlockingRequest, ctx: BlockingContext) -> BlockingStepResult:
            value = ctx.get("injected", 0)
            return BlockingStepResult(
                terminal=True,
                should_block=False,
                reason=f"got_{value}",
                step_name="use_ctx",
                details={},
            )

        pipeline = BlockingPipeline()
        pipeline.add_step("use_ctx", step_use_ctx)

        def init_ctx(req: BlockingRequest) -> BlockingContext:
            ctx = BlockingContext()
            ctx.set("injected", 42)
            return ctx

        decision, trace = pipeline.run(
            BlockingRequest(url="https://x.com/", domain="x.com"),
            context_initializer=init_ctx,
        )
        assert decision.should_block is False
        assert decision.reason == "got_42"
        assert len(trace) == 1
