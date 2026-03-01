"""Shared writing checkpoint utility for draft tools."""

import os


def auto_checkpoint_writing(filename: str, content: str, operation: str) -> None:
    """Auto-save writing session state to survive context compaction."""
    try:
        from med_paper_assistant.infrastructure.persistence import (
            get_workspace_state_manager,
        )

        wsm = get_workspace_state_manager()
        section = (
            os.path.splitext(os.path.basename(filename))[0]
            .replace("-", " ")
            .replace("_", " ")
            .title()
        )
        wsm.sync_writing_session(
            section=section,
            filename=filename,
            operation=operation,
            word_count=len(content.split()),
        )
    except Exception:
        pass  # Never fail the write due to checkpoint issues
