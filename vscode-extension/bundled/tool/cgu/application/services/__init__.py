"""The set of use cases, assembled from ports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from cgu.application.ports import ArchivePort, EmbeddingPort, LLMPort, RetrievalPort
from cgu.application.services.diverge import DivergeService
from cgu.application.services.evolve import EvolveService
from cgu.application.services.feedback import FeedbackService
from cgu.application.services.frame import FrameService
from cgu.application.services.ideas import IdeaService
from cgu.application.services.inquiry import InquiryService
from cgu.application.services.judge import JudgeService
from cgu.application.services.material import MaterialService
from cgu.application.services.question_gate import QuestionGateService
from cgu.application.services.session import SessionService


@dataclass
class Services:
    session: SessionService
    frame: FrameService
    material: MaterialService
    diverge: DivergeService
    ideas: IdeaService
    judge: JudgeService
    evolve: EvolveService
    feedback: FeedbackService
    question_gate: QuestionGateService
    inquiry: InquiryService


def build_services(
    archive: ArchivePort,
    embedding: EmbeddingPort,
    retrieval: RetrievalPort,
    llm: LLMPort | None,
    *,
    network_enabled: bool,
    execute_locally: bool,
    clock: Callable[[], datetime] | None = None,
) -> Services:
    ideas = IdeaService(archive, embedding)
    judge = JudgeService(archive)
    return Services(
        session=SessionService(archive),
        frame=FrameService(archive),
        material=MaterialService(archive, embedding, retrieval, network_enabled=network_enabled),
        diverge=DivergeService(archive, ideas, llm, execute_locally=execute_locally),
        ideas=ideas,
        judge=judge,
        evolve=EvolveService(archive, embedding, ideas, judge),
        feedback=FeedbackService(archive),
        question_gate=QuestionGateService(archive),
        inquiry=InquiryService(archive, embedding, clock=clock),
    )
