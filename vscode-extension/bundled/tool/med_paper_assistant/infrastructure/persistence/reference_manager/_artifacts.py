"""Persist and merge extracted source artifacts for a reference."""

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class ArtifactMixin:
    """Persist and merge extracted source artifacts for a reference."""

    def _copy_source_artifact(self, file_path: str | Path, ref_dir: str | Path) -> str:
        source_dir = os.path.join(os.fspath(ref_dir), "source")
        os.makedirs(source_dir, exist_ok=True)
        suffix = Path(file_path).suffix or ".bin"
        destination = os.path.join(source_dir, f"original{suffix}")
        shutil.copy2(file_path, destination)
        return destination

    def _persist_extracted_artifacts(self, ref_dir: str | Path, payload: Dict[str, Any]) -> None:
        """Persist extraction outputs and mint a hash-bound Asset-Aware receipt."""
        artifact_dir = self._write_extraction_outputs(ref_dir, payload)

        if not payload.get("fulltext_ingested") or not os.path.isdir(artifact_dir):
            return

        artifact_root = Path(artifact_dir)
        artifact_records = self._collect_artifact_records(artifact_root)
        if not artifact_records:
            return

        normalized_sections = self._normalize_fulltext_sections(payload.get("fulltext_sections"))
        asset_doc_id = str(payload.get("asset_aware_doc_id") or "").strip()
        if not asset_doc_id or not normalized_sections:
            return

        receipt_path = artifact_root / "receipt.json"
        receipt = self._build_fulltext_receipt(
            receipt_path, asset_doc_id, normalized_sections, artifact_records
        )
        self._write_json_file(str(receipt_path), receipt)
        payload["fulltext_receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    def _write_extraction_outputs(self, ref_dir: str | Path, payload: Dict[str, Any]) -> str:
        extracted_markdown = payload.get("extracted_markdown", "")
        manifest = payload.get("asset_aware_manifest")
        blocks = payload.get("asset_aware_blocks")
        segmentation = payload.get("asset_aware_segmentation")
        artifact_dir = os.path.join(os.fspath(ref_dir), "artifacts", "asset-aware")

        if extracted_markdown or manifest or blocks or segmentation:
            os.makedirs(artifact_dir, exist_ok=True)

        if extracted_markdown:
            with open(os.path.join(artifact_dir, "sections.md"), "w", encoding="utf-8") as handle:
                handle.write(extracted_markdown)

        if manifest:
            self._write_json_file(os.path.join(artifact_dir, "manifest.json"), manifest)

        if blocks:
            self._write_json_file(os.path.join(artifact_dir, "blocks.json"), blocks)

        if segmentation:
            self._write_json_file(os.path.join(artifact_dir, "segmentation.json"), segmentation)

        return artifact_dir

    def _collect_artifact_records(self, artifact_root: Path) -> list[dict[str, Any]]:
        artifact_records: list[dict[str, Any]] = []
        for artifact_path in sorted(artifact_root.iterdir()):
            if artifact_path.name == "receipt.json" or not artifact_path.is_file():
                continue
            raw = artifact_path.read_bytes()
            if not raw:
                continue
            artifact_records.append(
                {
                    "path": artifact_path.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
            )
        return artifact_records

    def _normalize_fulltext_sections(self, sections: Any) -> List[str]:
        if not isinstance(sections, list):
            return []
        return [str(section).strip() for section in sections if str(section).strip()]

    def _build_fulltext_receipt(
        self,
        receipt_path: Path,
        asset_doc_id: str,
        normalized_sections: List[str],
        artifact_records: list[dict[str, Any]],
    ) -> Dict[str, Any]:
        source_revision_payload = {
            "asset_aware_doc_id": asset_doc_id,
            "fulltext_sections": normalized_sections,
            "artifacts": artifact_records,
        }
        source_revision = hashlib.sha256(
            json.dumps(
                source_revision_payload,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        completed_at = datetime.now(timezone.utc).isoformat()
        existing_receipt = self._read_json_file(str(receipt_path), {})
        if (
            isinstance(existing_receipt, dict)
            and existing_receipt.get("source_revision_sha256") == source_revision
            and existing_receipt.get("asset_aware_doc_id") == asset_doc_id
            and existing_receipt.get("fulltext_sections") == normalized_sections
            and existing_receipt.get("artifacts") == artifact_records
            and isinstance(existing_receipt.get("completed_at"), str)
        ):
            completed_at = existing_receipt["completed_at"]

        return {
            "schema": "mdpaper.asset_aware_fulltext.v1",
            "source_tool": "asset-aware",
            "asset_aware_doc_id": asset_doc_id,
            "fulltext_sections": normalized_sections,
            "completed_at": completed_at,
            "source_revision_sha256": source_revision,
            "artifacts": artifact_records,
        }

    def _files_have_same_content(self, source_path: str, target_path: str) -> bool:
        if not os.path.exists(source_path) or not os.path.exists(target_path):
            return False
        if os.path.getsize(source_path) != os.path.getsize(target_path):
            return False
        return self.compute_content_hash(source_path) == self.compute_content_hash(target_path)

    def _build_conflict_copy_path(self, target_path: str, source_ref_id: str) -> str:
        target = Path(target_path)
        suffix = "".join(target.suffixes)
        stem = target.name[: -len(suffix)] if suffix else target.name
        candidate = target.with_name(f"{stem}.from-{source_ref_id}{suffix}")
        counter = 2

        while candidate.exists():
            candidate = target.with_name(f"{stem}.from-{source_ref_id}.{counter}{suffix}")
            counter += 1

        return str(candidate)

    def _merge_artifact_tree(
        self,
        source_dir: str,
        target_dir: str,
        source_ref_id: str,
        target_root_dir: str,
    ) -> List[str]:
        conflicts: List[str] = []

        for root, _, files in os.walk(source_dir):
            relative_root = os.path.relpath(root, source_dir)
            destination_root = (
                target_dir if relative_root == "." else os.path.join(target_dir, relative_root)
            )
            os.makedirs(destination_root, exist_ok=True)

            for file_name in files:
                source_path = os.path.join(root, file_name)
                destination_path = os.path.join(destination_root, file_name)

                if not os.path.exists(destination_path):
                    shutil.copy2(source_path, destination_path)
                    continue

                if self._files_have_same_content(source_path, destination_path):
                    continue

                conflict_path = self._build_conflict_copy_path(destination_path, source_ref_id)
                shutil.copy2(source_path, conflict_path)
                conflicts.append(os.path.relpath(conflict_path, target_root_dir))

        return conflicts

    def _merge_reference_artifacts(
        self, source_ref_dir: str | Path, target_ref_dir: str | Path
    ) -> List[str]:
        """Merge durable artifacts from one reference directory into another."""
        source_ref_dir = os.fspath(source_ref_dir)
        target_ref_dir = os.fspath(target_ref_dir)
        if not os.path.exists(source_ref_dir) or source_ref_dir == target_ref_dir:
            return []

        source_ref_id = os.path.basename(source_ref_dir)
        conflicts: List[str] = []

        for relative_dir in ("source", os.path.join("artifacts", "asset-aware")):
            source_dir = os.path.join(source_ref_dir, relative_dir)
            target_dir = os.path.join(target_ref_dir, relative_dir)
            if os.path.isdir(source_dir):
                os.makedirs(target_dir, exist_ok=True)
                conflicts.extend(
                    self._merge_artifact_tree(
                        source_dir,
                        target_dir,
                        source_ref_id,
                        target_ref_dir,
                    )
                )

        source_analysis = os.path.join(source_ref_dir, "analysis.json")
        target_analysis = os.path.join(target_ref_dir, "analysis.json")
        if os.path.exists(source_analysis):
            if not os.path.exists(target_analysis):
                shutil.copy2(source_analysis, target_analysis)
            elif not self._files_have_same_content(source_analysis, target_analysis):
                conflict_path = self._build_conflict_copy_path(target_analysis, source_ref_id)
                shutil.copy2(source_analysis, conflict_path)
                conflicts.append(os.path.relpath(conflict_path, target_ref_dir))

        return conflicts
