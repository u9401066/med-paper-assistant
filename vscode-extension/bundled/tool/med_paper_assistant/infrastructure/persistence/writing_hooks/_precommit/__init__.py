"""Writing Hooks — Pre-commit hooks mixin (P5: protected content, P6: memory, P7: ref integrity)."""

from __future__ import annotations

from ._memory import MemorySyncHooksMixin
from ._protected import ProtectedContentHooksMixin
from ._references import ReferenceIntegrityHooksMixin


class PreCommitMixin(
    ProtectedContentHooksMixin,
    ReferenceIntegrityHooksMixin,
    MemorySyncHooksMixin,
):
    """P-series hooks that have their own implementation (not delegations)."""


__all__ = ["PreCommitMixin"]
