"""MedPaper-managed Foam graph named views (``foam.graph.views``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import structlog

from med_paper_assistant.shared.slug import slugify_token

logger = structlog.get_logger()

MANAGED_GRAPH_VIEW_NAMES = ["Default", "Evidence", "Writing", "Assets", "Review"]
_HIDDEN_COLOR = "#d9d9d9"

_GROUP_SPECS = (
    ("reference", "type", "reference", "#2c7da0"),
    ("knowledge-map", "type", "knowledge-map", "#588157"),
    ("synthesis-page", "type", "synthesis-page", "#6a4c93"),
    ("library-overview", "type", "library-overview", "#457b9d"),
    ("library-dashboard", "type", "library-dashboard", "#5a7d9a"),
    ("library-review", "type", "library-review", "#c46b48"),
    ("library-daily", "type", "library-daily", "#6c757d"),
    ("publish-index", "type", "publish-index", "#264653"),
    ("publish-links", "type", "publish-links", "#2a9d8f"),
    ("draft-section", "type", "draft-section", "#ffb703"),
    ("figure-note", "type", "figure-note", "#e76f51"),
    ("table-note", "type", "table-note", "#8d99ae"),
    ("literature", "note_domain", "literature", "#277da1"),
    ("writing", "note_domain", "writing", "#f4a261"),
    ("asset", "note_domain", "asset", "#c9184a"),
    ("synthesis", "note_domain", "synthesis", "#6d597a"),
    ("library", "note_domain", "library", "#457b9d"),
    ("export", "note_domain", "export", "#2a9d8f"),
    ("methods", "section_kind", "methods", "#bc6c25"),
    ("results", "section_kind", "results", "#2a9d8f"),
    ("discussion", "section_kind", "discussion", "#9b5de5"),
    ("figure-assets", "asset_type", "figure", "#ef476f"),
    ("table-assets", "asset_type", "table", "#118ab2"),
)


def group(
    group_id: str, property_name: str, value: str, color: str, *, enabled: bool = True
) -> Dict[str, Any]:
    return {
        "id": group_id,
        "label": f"{property_name}={value}",
        "color": color,
        "enabled": enabled,
        "match": {"property": property_name, "value": value},
    }


def _hidden_domain(domain: str, group_id: str | None = None) -> Dict[str, Any]:
    return group(group_id or f"hide-{domain}", "note_domain", domain, _HIDDEN_COLOR, enabled=False)


def _view(
    name: str,
    background: str,
    line_color: str,
    show: Dict[str, Any],
    groups: List[Dict[str, Any]],
    color_by: str = "type",
    font_size: int = 12,
) -> Dict[str, Any]:
    return {
        "name": name,
        "colorBy": color_by,
        "background": background,
        "lineColor": line_color,
        "fontSize": font_size,
        "show": show,
        "groups": groups,
    }


def _default_show() -> Dict[str, Any]:
    return {
        "tag": {"enabled": False, "color": "#f4d35e"},
        "placeholder": {"enabled": False, "color": "#c7ced6"},
        "attachment": {"enabled": False, "color": "#7d8597"},
        "image": {"enabled": False, "color": "#ff99c8"},
    }


def build_graph_groups(current_slug: str) -> List[Dict[str, Any]]:
    """Reusable graph groups for the MedPaper note taxonomy."""
    groups = [group("project", "project", current_slug, "#1d3557")]
    groups.extend(group(*spec) for spec in _GROUP_SPECS)
    return groups


def build_graph_views(
    current_slug: str, custom_views: List[Dict[str, Any]] | None = None
) -> List[Dict[str, Any]]:
    """Generate MedPaper-managed Foam named views for the active project."""
    groups = build_graph_groups(current_slug)
    show = _default_show()
    asset_show = {
        **show,
        "attachment": {"enabled": True, "color": "#7d8597"},
        "image": {"enabled": True, "color": "#ff99c8"},
    }
    review_groups = [
        group("review-pending", "review_state", "pending", "#f07167"),
        group("review-reviewed", "review_state", "reviewed", "#2a9d8f"),
        group("analysis-pending", "analysis_state", "pending", "#f4a261"),
        group("fulltext-missing", "fulltext_state", "missing", "#e76f51"),
    ]
    managed = [
        _view("Default", "#fbfcff", "#7a8ca5", show, groups),
        _view(
            "Evidence",
            "#fcfffd",
            "#7f9c8d",
            show,
            [*groups, _hidden_domain("writing"), _hidden_domain("asset", "hide-assets")],
        ),
        _view(
            "Writing",
            "#fffdf7",
            "#c49a5a",
            show,
            [*groups, _hidden_domain("literature"), _hidden_domain("synthesis")],
        ),
        _view(
            "Assets",
            "#fffafc",
            "#b86c8b",
            asset_show,
            [*groups, *(_hidden_domain(d) for d in ("literature", "writing", "synthesis"))],
        ),
        _view("Review", "#fffdfb", "#ae7f5a", show, [*groups, *review_groups]),
    ]
    return managed + build_custom_graph_views(groups, show, custom_views or [])


def merge_graph_views(existing: Any, generated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Preserve non-MedPaper custom views while replacing managed ones."""
    generated_names = {
        str(view.get("name", "")).strip() for view in generated if isinstance(view, dict)
    }
    preserved: List[Dict[str, Any]] = []
    for view in existing if isinstance(existing, list) else []:
        if not isinstance(view, dict):
            continue
        name = str(view.get("name", "")).strip()
        if name and name not in generated_names and name not in MANAGED_GRAPH_VIEW_NAMES:
            preserved.append(view)
    return generated + preserved


def load_project_custom_graph_views(projects_dir: Path, current_slug: str) -> List[Dict[str, Any]]:
    project_config_path = projects_dir / current_slug / "project.json"
    if not project_config_path.exists():
        return []
    try:
        config = json.loads(project_config_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Failed to load project config for custom graph views", exc_info=True)
        return []

    settings = config.get("settings", {}) if isinstance(config, dict) else {}
    custom_views = settings.get("custom_graph_views", []) if isinstance(settings, dict) else []
    if not isinstance(custom_views, list):
        return []
    return [view for view in custom_views if isinstance(view, dict)]


def _hide_groups(group_id: str, hide_specs: Any) -> List[Dict[str, Any]]:
    hidden: List[Dict[str, Any]] = []
    for hide_index, hide_spec in enumerate(
        hide_specs if isinstance(hide_specs, list) else [], start=1
    ):
        if not isinstance(hide_spec, dict):
            continue
        hide_property = str(hide_spec.get("property") or "").strip()
        hide_value = str(hide_spec.get("value") or "").strip()
        if not hide_property or not hide_value:
            continue
        hide_color = str(hide_spec.get("color") or _HIDDEN_COLOR)
        hidden.append(
            group(
                f"{group_id}-hide-{hide_index}",
                hide_property,
                hide_value,
                hide_color,
                enabled=False,
            )
        )
    return hidden


def build_custom_graph_views(
    base_groups: List[Dict[str, Any]],
    default_show: Dict[str, Any],
    custom_views: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    generated: List[Dict[str, Any]] = []
    for index, spec in enumerate(custom_views, start=1):
        name = str(spec.get("name", "")).strip()
        raw_match = spec.get("match")
        match: dict[str, Any] = raw_match if isinstance(raw_match, dict) else {}
        property_name = str(match.get("property") or spec.get("property") or "").strip()
        value = str(match.get("value") or spec.get("value") or "").strip()
        if not name or not property_name or not value:
            continue

        group_id = f"custom-{slugify_token(name, fallback='view')}-{index}"
        view_groups = [
            *base_groups,
            group(group_id, property_name, value, str(spec.get("color") or "#457b9d")),
            *_hide_groups(group_id, spec.get("hide", [])),
        ]
        generated.append(
            _view(
                name,
                str(spec.get("background") or "#f8fbff"),
                str(spec.get("lineColor") or "#7a8ca5"),
                default_show,
                view_groups,
                color_by=str(spec.get("colorBy") or "type"),
                font_size=int(spec.get("fontSize") or 12),
            )
        )
    return generated
