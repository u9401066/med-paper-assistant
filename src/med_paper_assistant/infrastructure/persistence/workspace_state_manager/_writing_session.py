"""Writing-session auto-checkpoint."""

from datetime import datetime

from ._io import StateIOMixin


class WritingSessionMixin(StateIOMixin):
    """Persist writing-session progress so it survives context compaction."""

    def sync_writing_session(
        self,
        section: str,
        filename: str,
        operation: str,
        word_count: int = 0,
        agent_context: str | None = None,
    ) -> bool:
        """
        Auto-checkpoint writing session state.

        Called automatically by write_draft/patch_draft after successful writes.
        Survives context compaction so the agent can recover writing progress.

        Args:
            section: Section name being written (e.g., "Introduction").
            filename: Draft filename modified.
            operation: "write" or "patch".
            word_count: Current word count of the file.
            agent_context: Optional agent notes about current writing intent.
        """
        state = self.get_state()

        # Scan drafts/ to capture all sections on disk
        sections_on_disk = []
        slug = self._get_current_project_slug()
        if slug:
            try:
                drafts_dir = self._project_dir(slug) / "drafts"
            except ValueError:
                drafts_dir = None
            if drafts_dir is not None and drafts_dir.is_dir():
                for f in sorted(drafts_dir.iterdir()):
                    if f.suffix == ".md":
                        name = f.stem.replace("-", " ").replace("_", " ").title()
                        wc = len(f.read_text(encoding="utf-8").split())
                        sections_on_disk.append(f"{name} ({wc}w)")

        state["writing_session"] = {
            "active": True,
            "current_section": section,
            "last_file_modified": filename,
            "last_operation": operation,
            "word_count": word_count,
            "sections_on_disk": sections_on_disk,
            "timestamp": datetime.now().isoformat(),
            "agent_context": agent_context,
        }

        # Also update recovery hints as double-safety
        state["recovery_hints"]["agent_was_doing"] = f"Writing {section} ({operation} → {filename})"
        state["last_activity"] = datetime.now().isoformat()

        return self.save_state(state)
