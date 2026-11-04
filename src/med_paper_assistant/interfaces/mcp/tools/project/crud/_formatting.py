"""Workflow-aware text blocks shared by the project CRUD handlers."""


def contents_block(stats: dict[str, object], workflow_mode: str) -> str:
    if workflow_mode == "library-wiki":
        return (
            f"- 📥 Inbox notes: {stats.get('inbox', 0)} files\n"
            f"- 🧠 Concept notes: {stats.get('concepts', 0)} files\n"
            f"- 🗂️ Synthesis projects: {stats.get('projects', 0)} files\n"
            f"- 📚 References: {stats.get('references', 0)} saved"
        )

    return (
        f"- 📝 Drafts: {stats.get('drafts', 0)} files\n"
        f"- 📚 References: {stats.get('references', 0)} saved\n"
        f"- 📊 Data files: {stats.get('data_files', 0)}"
    )


def paths_block(paths: dict[str, str], workflow_mode: str) -> str:
    if workflow_mode == "library-wiki":
        return (
            f"- Concept seed: `{paths.get('concept', '')}`\n"
            f"- Inbox: `{paths.get('inbox', '')}`\n"
            f"- Concepts: `{paths.get('concepts', '')}`\n"
            f"- Projects: `{paths.get('projects', '')}`\n"
            f"- References: `{paths.get('references', '')}`"
        )

    return (
        f"- Concept: `{paths.get('concept', '')}`\n"
        f"- Drafts: `{paths.get('drafts', '')}`\n"
        f"- References: `{paths.get('references', '')}`\n"
        f"- Data: `{paths.get('data', '')}`\n"
        f"- Results: `{paths.get('results', '')}`"
    )


def stats_table(stats: dict[str, object], workflow_mode: str) -> str:
    if workflow_mode == "library-wiki":
        rows = [
            f"| Inbox Notes | {stats.get('inbox', 0)} |",
            f"| Concept Notes | {stats.get('concepts', 0)} |",
            f"| Synthesis Projects | {stats.get('projects', 0)} |",
            f"| References | {stats.get('references', 0)} |",
        ]
    else:
        rows = [
            f"| Drafts | {stats.get('drafts', 0)} |",
            f"| References | {stats.get('references', 0)} |",
            f"| Data Files | {stats.get('data_files', 0)} |",
        ]
    return "\n".join(rows)


def detail_paths(paths: dict[str, str], workflow_mode: str) -> dict[str, str]:
    if workflow_mode == "library-wiki":
        return {
            "project_root": paths.get("root", ""),
            "concept": paths.get("concept", ""),
            "inbox_dir": paths.get("inbox", ""),
            "concepts_dir": paths.get("concepts", ""),
            "projects_dir": paths.get("projects", ""),
            "references_dir": paths.get("references", ""),
        }

    return {
        "project_root": paths.get("root", ""),
        "concept": paths.get("concept", ""),
        "drafts_dir": paths.get("drafts", ""),
        "references_dir": paths.get("references", ""),
        "data_dir": paths.get("data", ""),
        "results_dir": paths.get("results", ""),
    }
