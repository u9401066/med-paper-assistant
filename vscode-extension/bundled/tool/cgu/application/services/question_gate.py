"""Question gate: a question must earn its depth before it is worth asking."""

from __future__ import annotations

from cgu.application.ports import ArchivePort
from cgu.application.services._common import (
    frame_summary,
    now_iso,
    provenance,
    require_frame,
    require_session,
)
from cgu.application.services.instructions import question_gate_order
from cgu.domain.common import CGUError, ToolResult
from cgu.domain.doubt import QuestionVerdicts, evaluate_question_gate


class QuestionGateService:
    def __init__(self, archive: ArchivePort) -> None:
        self._archive = archive

    async def check(
        self,
        session_id: str,
        question: str | None,
        frame_id: str | None,
        decision_context: str | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not question or not question.strip():
            raise CGUError("invalid_input", "question is required for action=check")
        if not decision_context or not decision_context.strip():
            raise CGUError(
                "invalid_input",
                "decision_context is required for action=check",
                "Say which decision this question is supposed to inform.",
            )
        summary = None
        if frame_id:
            summary = frame_summary(await require_frame(self._archive, session_id, frame_id))
        order = question_gate_order(
            session_id=session_id,
            question=question.strip(),
            decision_context=decision_context.strip(),
            frame_summary=summary,
        )
        return ToolResult.success(
            provenance("passthrough", seed=session.seed),
            {"requires_execution_by_caller": True},
            work_order=order,
        )

    async def record(
        self,
        session_id: str,
        question: str | None,
        verdicts: QuestionVerdicts | None,
        judge_model: str | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not question or not question.strip() or verdicts is None:
            raise CGUError("invalid_input", "question and verdicts are required for action=record")
        result = evaluate_question_gate(verdicts)
        await self._archive.save_question(
            session_id,
            {
                "question": question.strip(),
                "verdicts": verdicts.model_dump(),
                "passed": result.passed,
                "failed": result.failed,
                "judge_model": judge_model,
                "at": now_iso(),
            },
        )
        warnings = []
        if not judge_model:
            warnings.append("judge_model not given; the verdict cannot be audited")
        return ToolResult.success(
            provenance("heuristic", seed=session.seed, warnings=warnings),
            {
                "passed": result.passed,
                "failed_criteria": result.failed,
                "non_typical": result.non_typical,
                "rule": "passed only if decision_relevant, operable, load_bearing and non_verbal "
                "are all true; non_typical is a bonus, never a veto",
            },
        )
