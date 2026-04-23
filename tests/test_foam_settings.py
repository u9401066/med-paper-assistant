from __future__ import annotations

import json

from med_paper_assistant.infrastructure.services.foam_settings import FoamSettingsManager


def test_update_for_project_writes_graph_views_and_preview_navigation(tmp_path) -> None:
    settings_dir = tmp_path / ".vscode"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    (tmp_path / "projects" / "alpha").mkdir(parents=True)
    (tmp_path / "projects" / "beta").mkdir(parents=True)

    manager = FoamSettingsManager(tmp_path)
    result = manager.update_for_project("alpha")

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    views = settings["foam.graph.views"]
    view_names = [view["name"] for view in views]

    assert result["success"] is True
    assert result["graph_views"] == ["Default", "Evidence", "Writing", "Assets", "Review"]
    assert settings["foam.graph.navigateToPreview"] is True
    assert view_names[:5] == ["Default", "Evidence", "Writing", "Assets", "Review"]
    assert any(group["match"] == {"property": "type", "value": "draft-section"} for group in views[0]["groups"])
    assert any(group["match"] == {"property": "asset_type", "value": "figure"} for group in views[0]["groups"])
    assert any(group["match"] == {"property": "type", "value": "library-dashboard"} for group in views[0]["groups"])
    assert "projects/beta/**" in settings["foam.files.ignore"]


def test_update_for_project_preserves_custom_non_managed_views(tmp_path) -> None:
    settings_dir = tmp_path / ".vscode"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "foam.graph.views": [
                    {
                        "name": "Journal Club",
                        "colorBy": "directory",
                    },
                    {
                        "name": "Default",
                        "colorBy": "none",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "projects" / "alpha").mkdir(parents=True)

    manager = FoamSettingsManager(tmp_path)
    manager.update_for_project("alpha")

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    views = settings["foam.graph.views"]
    view_names = [view["name"] for view in views]

    assert view_names[:5] == ["Default", "Evidence", "Writing", "Assets", "Review"]
    assert view_names[5:] == ["Journal Club"]


def test_update_for_project_reads_custom_graph_views_from_project_settings(tmp_path) -> None:
    settings_dir = tmp_path / ".vscode"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    project_dir = tmp_path / "projects" / "alpha"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        json.dumps(
            {
                "settings": {
                    "custom_graph_views": [
                        {
                            "name": "Sedation Focus",
                            "property": "tags",
                            "value": "sedation",
                            "color": "#457b9d",
                            "background": "#f8fbff",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    manager = FoamSettingsManager(tmp_path)
    result = manager.update_for_project("alpha")

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    views = settings["foam.graph.views"]
    view_names = [view["name"] for view in views]
    sedation_view = next(view for view in views if view["name"] == "Sedation Focus")

    assert result["success"] is True
    assert "Sedation Focus" in result["graph_views"]
    assert "Sedation Focus" in view_names
    assert any(group["match"] == {"property": "tags", "value": "sedation"} for group in sedation_view["groups"])