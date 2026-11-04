"""Deletion of saved references."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from med_paper_assistant.shared.path_guard import PathGuardError


class ReferenceDeletionMixin:
    """Preview and perform deletion of a saved reference."""

    def delete_reference(self, pmid: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a saved reference and all associated files.

        Args:
            pmid: PubMed ID of the reference to delete.
            confirm: Must be True to actually delete.

        Returns:
            Dict with success status and deleted files info.
        """
        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError) as exc:
            return {"success": False, "error": f"Invalid reference id: {exc}"}

        precheck_error = self._deletion_precheck(pmid, ref_dir)
        if precheck_error:
            return precheck_error

        # Get reference info before deletion for confirmation
        summary = self.get_reference_summary(pmid)
        title = summary.get("title", "Unknown title")
        citation_key = summary.get("citation_key", f"pmid_{pmid}")

        if not confirm:
            return self._deletion_preview(pmid, title, citation_key, ref_dir)

        try:
            deleted_files = self._execute_deletion(pmid, ref_dir)
            return {
                "success": True,
                "pmid": pmid,
                "title": title,
                "citation_key": citation_key,
                "deleted_files": deleted_files,
                "message": f"✅ 已刪除 PMID {pmid}: {title}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"刪除失敗: {str(e)}",
                "pmid": pmid,
            }

    def _deletion_preview(
        self, pmid: str, title: str, citation_key: str, ref_dir: Path
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "requires_confirmation": True,
            "pmid": pmid,
            "title": title,
            "citation_key": citation_key,
            "files_to_delete": self._list_relative_files(ref_dir),
            "message": f"⚠️ 即將刪除 PMID {pmid}。請確認後使用 confirm=True 執行刪除。",
        }

    def _execute_deletion(self, pmid: str, ref_dir: Path) -> List[str]:
        deleted_files = self._list_relative_files(ref_dir)

        metadata = self.get_metadata(pmid)
        self._remove_identity_registry_entries(pmid, metadata)
        shutil.rmtree(ref_dir)
        self._rebuild_index()
        if metadata:
            self._append_log("delete_reference", metadata)
        return deleted_files

    def _deletion_precheck(self, pmid: str, ref_dir: Path) -> Optional[Dict[str, Any]]:
        if not os.path.exists(ref_dir):
            return {
                "success": False,
                "error": f"Reference {pmid} not found in local library.",
            }

        if not os.path.exists(os.path.join(ref_dir, "metadata.json")):
            return {
                "success": False,
                "error": f"Reference {pmid} is missing metadata.json; refusing deletion.",
            }
        return None

    def _list_relative_files(self, ref_dir: Path) -> List[str]:
        relative_files = []
        for root, dirs, files in os.walk(ref_dir):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), ref_dir)
                relative_files.append(rel_path)
        return relative_files
