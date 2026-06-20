"""Pydantic schemas for the Action Debug Runner API."""

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class StepStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DebugRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class DebugStep(BaseModel):
    """One /interact call — either a natural-language prompt or executable code."""

    prompt: str | None = Field(
        default=None,
        min_length=1,
        description="Plain-English instruction for /interact prompt mode",
        examples=["Click the login button"],
    )
    code: str | None = Field(
        default=None,
        min_length=1,
        description="Playwright or bash code for /interact code mode",
        examples=["await page.click('#login'); true"],
    )
    language: str | None = Field(
        default=None,
        description="Code language: node (default), python, or bash",
        examples=["bash"],
    )

    @model_validator(mode="after")
    def require_prompt_or_code(self) -> "DebugStep":
        has_prompt = bool(self.prompt and self.prompt.strip())
        has_code = bool(self.code and self.code.strip())
        if has_prompt == has_code:
            raise ValueError("Provide exactly one of 'prompt' or 'code'")
        return self

    def action_label(self) -> str:
        if self.prompt:
            text = self.prompt.strip()
            return text if len(text) <= 120 else f"{text[:117]}..."
        assert self.code is not None
        first_line = self.code.strip().splitlines()[0]
        return first_line if len(first_line) <= 120 else f"{first_line[:117]}..."


class DebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running steps")
    steps: list[DebugStep] = Field(
        min_length=1,
        description="Ordered /interact steps (prompt or code each)",
        examples=[
            [
                {"prompt": "Wait for the page to finish loading"},
                {"code": "await page.click('#login'); true"},
            ]
        ],
    )


class StepResult(BaseModel):
    index: int = Field(description="1-based step index")
    action: str = Field(description="Prompt or code sent for this step")
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
    screenshot_base64: str | None = Field(
        default=None,
        description="Page screenshot at failure time (base64 PNG)",
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
