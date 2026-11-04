"""Provenance recording helpers for the statistical analysis tools."""

from pathlib import Path
from typing import Optional

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
from med_paper_assistant.infrastructure.services.analyzer import Analyzer


def _get_tracker(project_info: dict) -> DataArtifactTracker | None:
    """Create a DataArtifactTracker for the current project, or None if no project."""
    if not project_info or not project_info.get("project_path"):
        return None
    project_dir = Path(project_info["project_path"])
    return DataArtifactTracker(project_dir / ".audit", project_dir)


def _require_project_info(project_info: dict | None) -> dict:
    """Convert optional project metadata into an explicit runtime guard."""
    if project_info is None:
        raise RuntimeError(
            "Project context resolved without project metadata while recording provenance."
        )
    return project_info


def _scoped_analyzer(analyzer: Analyzer, project_info: dict | None) -> Analyzer:
    """Bind analysis I/O to the resolved project without mutating shared server state."""
    if project_info and project_info.get("project_path"):
        return analyzer.scoped_to_project(project_info["project_path"])
    return analyzer


def _record_test_provenance(
    filename: str,
    test_type: str,
    group_var: Optional[str],
    project_info: dict | None,
    result: str,
    var_list: list[str],
) -> None:
    # Record provenance
    tracker = _get_tracker(project_info) if project_info else None
    if tracker:
        params = {
            "filename": filename,
            "test_type": test_type,
            "variables": var_list,
            "group_var": group_var,
        }
        vars_str = ", ".join(f"'{v}'" for v in var_list)
        group_arg = f", group_var='{group_var}'" if group_var else ""
        tracker.record_artifact(
            tool_name="run_statistical_test",
            artifact_type="statistics",
            parameters=params,
            data_source=filename,
            result_summary=result[:300] if result else None,
            provenance_code=(
                f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                f"analyzer = Analyzer()\n"
                f"result = analyzer.run_statistical_test(\n"
                f"    filename='{filename}',\n"
                f"    test_type='{test_type}',\n"
                f"    variables=[{vars_str}]{group_arg},\n"
                f")\n"
                f"print(result)"
            ),
        )


def _relative_output_path(result: str, project_info: dict) -> str:
    """Compute the output path relative to the project dir (falls back to the raw path)."""
    try:
        return str(Path(result).relative_to(Path(project_info["project_path"])))
    except (ValueError, KeyError):
        return result


def _record_plot_provenance(
    filename: str,
    plot_type: str,
    x_var: str,
    y_var: Optional[str],
    hue_var: Optional[str],
    title: Optional[str],
    output_name: Optional[str],
    project_info: dict | None,
    result: str,
) -> None:
    # Record provenance — result is the output file path
    tracker = _get_tracker(project_info) if project_info else None
    if tracker and result and not result.startswith("Error"):
        project_info = _require_project_info(project_info)
        rel_path = _relative_output_path(result, project_info)

        params = {
            "filename": filename,
            "plot_type": plot_type,
            "x_var": x_var,
            "y_var": y_var,
            "hue_var": hue_var,
            "title": title,
            "output_name": output_name,
        }
        y_arg = f", y_col='{y_var}'" if y_var else ""
        hue_arg = f", hue_col='{hue_var}'" if hue_var else ""
        title_arg = f", title='{title}'" if title else ""
        out_arg = f", output_name='{output_name}'" if output_name else ""
        tracker.record_artifact(
            tool_name="create_plot",
            artifact_type="figure",
            parameters=params,
            output_path=rel_path,
            data_source=filename,
            provenance_code=(
                f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                f"analyzer = Analyzer()\n"
                f"path = analyzer.create_plot(\n"
                f"    filename='{filename}',\n"
                f"    plot_type='{plot_type}',\n"
                f"    x_col='{x_var}'{y_arg}{hue_arg}{title_arg}{out_arg},\n"
                f")\n"
                f"print(f'Saved to: {{path}}')"
            ),
        )


def _record_table_provenance(
    filename: str,
    group_col: str,
    output_name: Optional[str],
    categorical_list: list[str],
    continuous_list: list[str],
    project_info: dict | None,
    result: str,
) -> None:
    # Record provenance
    tracker = _get_tracker(project_info) if project_info else None
    if tracker:
        params = {
            "filename": filename,
            "group_col": group_col,
            "continuous_cols": continuous_list,
            "categorical_cols": categorical_list,
            "output_name": output_name,
        }
        # Compute output path if saved to file
        output_rel = None
        if output_name:
            oname = output_name if output_name.endswith(".md") else output_name + ".md"
            output_rel = f"results/tables/{oname}"

        cont_str = ", ".join(f"'{c}'" for c in continuous_list)
        cat_str = ", ".join(f"'{c}'" for c in categorical_list)
        out_arg = f", output_name='{output_name}'" if output_name else ""
        tracker.record_artifact(
            tool_name="generate_table_one",
            artifact_type="table",
            parameters=params,
            output_path=output_rel,
            data_source=filename,
            result_summary=result[:200] if result else None,
            provenance_code=(
                f"from med_paper_assistant.infrastructure.services.analyzer import Analyzer\n"
                f"analyzer = Analyzer()\n"
                f"result = analyzer.generate_table_one(\n"
                f"    filename='{filename}',\n"
                f"    group_col='{group_col}',\n"
                f"    continuous_cols=[{cont_str}],\n"
                f"    categorical_cols=[{cat_str}]{out_arg},\n"
                f")\n"
                f"print(result)"
            ),
        )
