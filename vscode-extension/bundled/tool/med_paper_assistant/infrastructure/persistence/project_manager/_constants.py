"""Constants shared by the ProjectManager mixins."""

# Current project state file
PROJECT_STATE_FILE = ".current_project"

# Valid project statuses
PROJECT_STATUSES = ["concept", "drafting", "review", "submitted", "published"]

# Temporary project for exploration
TEMP_EXPLORATION_SLUG = "temp-exploration"

TEMP_PROJECT_DESCRIPTION = (
    "臨時工作區 - 用於探索文獻，尋找研究靈感。找到有興趣的主題後可轉換為正式專案。"
)
TEMP_PROJECT_MEMO = (
    "這是一個暫存專案，用於文獻探索。使用 convert_temp_to_project 可將內容轉移到正式專案。"
)
TEMP_PROJECT_SEED_MEMO = "這是一個暫存專案，用於文獻探索與 wiki 整理。"
TEMP_PROJECT_CREATED_MESSAGE = (
    "✅ 已建立文獻探索工作區！\n\n"
    "現在可以自由搜尋和保存文獻。找到研究方向後，使用 convert_temp_to_project 將內容轉移到正式專案。"
)
