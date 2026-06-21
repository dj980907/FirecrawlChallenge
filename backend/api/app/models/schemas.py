"""Pydantic schemas for the Action Debug Runner API."""

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class StepStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DebugRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class InteractLanguage(StrEnum):
    NODE = "node"
    PYTHON = "python"
    BASH = "bash"


class DebugStep(BaseModel):
    """Internal /interact code step executed by the debug runner."""

    code: str = Field(min_length=1)
    language: InteractLanguage | None = None

    def action_label(self) -> str:
        first_line = self.code.strip().splitlines()[0]
        return first_line if len(first_line) <= 120 else f"{first_line[:117]}..."


class CodeBlockDebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running steps")
    code_block: str = Field(
        min_length=1,
        description="Script to split into /interact steps (Node, Python, or bash)",
    )
    language: InteractLanguage = Field(
        default=InteractLanguage.NODE,
        description="Language for /interact code mode: node, python, or bash",
    )


class StepResult(BaseModel):
    index: int = Field(description="1-based step index")
    action: str = Field(description="Code sent for this step")
    status: StepStatus
    duration_ms: int
    error: str | None = None
    output: str | None = Field(
        default=None,
        description="/interact output field when present",
    )
    live_view_url: str | None = Field(
        default=None,
        description="Read-only live browser stream URL from /interact",
    )


class DebugRunResponse(BaseModel):
    status: DebugRunStatus
    failed_at_step: int | None = Field(
        default=None,
        description="1-based index of the first failed step, if any",
    )
    total_steps: int
    total_duration_ms: int
    steps: list[StepResult]
    page_content: str | None = Field(
        default=None,
        description="Final page text when all steps pass",
    )
    scrape_id: str | None = Field(
        default=None,
        description="Firecrawl scrape session ID used for this run",
    )
    parsed_steps: list[str] | None = Field(
        default=None,
        description="Code snippets produced by splitting code_block",
    )
    step_summaries: list[str] | None = Field(
        default=None,
        description="Human-readable step labels when split with AI",
    )
