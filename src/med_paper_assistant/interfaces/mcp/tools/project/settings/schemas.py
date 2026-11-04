"""Pydantic models used to elicit project settings."""

from pydantic import BaseModel, Field

from med_paper_assistant.domain.paper_types import PAPER_TYPES


class PaperTypeSchema(BaseModel):
    """Schema for paper type selection - uses enum for dropdown."""

    paper_type: str = Field(
        description="Type of paper",
        json_schema_extra={
            "enum": list(PAPER_TYPES),
            "enumNames": [profile.name for profile in PAPER_TYPES.values()],
        },
    )


class ProjectSetupSchema(PaperTypeSchema):
    """Single-round input for the MCP SDK 2 project setup resolver."""

    interaction_style: str = Field(
        default="",
        description="Optional interaction preference, for example '中文回答' or 'Be concise'",
    )
    language_preference: str = Field(
        default="",
        description="Optional preferred language for responses and drafts",
    )
    writing_style: str = Field(
        default="",
        description="Optional academic writing style guidance",
    )
    memo: str = Field(
        default="",
        description="Optional project notes such as deadlines, co-authors, or IRB details",
    )
