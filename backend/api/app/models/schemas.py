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


class InteractLanguage(StrEnum):
    NODE = "node"
    PYTHON = "python"
    BASH = "bash"


def normalize_interact_language(language: str | InteractLanguage | None) -> InteractLanguage:
    if language is None:
        return InteractLanguage.NODE
    if isinstance(language, InteractLanguage):
        return language

    value = language.strip().lower()
    aliases = {
        "node": InteractLanguage.NODE,
        "javascript": InteractLanguage.NODE,
        "js": InteractLanguage.NODE,
        "python": InteractLanguage.PYTHON,
        "py": InteractLanguage.PYTHON,
        "bash": InteractLanguage.BASH,
        "shell": InteractLanguage.BASH,
    }
    try:
        return aliases[value]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported language {language!r}. Use node, python, or bash."
        ) from exc


class DebugStep(BaseModel):
    """Internal step model — exactly one of prompt or code."""

    prompt: str | None = None
    code: str | None = None
    language: str | None = None

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


class CodeDebugStep(BaseModel):
    code: str = Field(
        min_length=1,
        description="Playwright or bash code for /interact code mode",
        examples=["await page.click('#login'); true"],
    )
    language: InteractLanguage | None = Field(
        default=None,
        description="Code language: node (default), python, or bash",
        examples=["bash"],
    )

    def to_debug_step(self) -> DebugStep:
        lang = self.language.value if self.language else None
        return DebugStep(code=self.code, language=lang)


class PromptDebugStep(BaseModel):
    prompt: str = Field(
        min_length=1,
        description="Plain-English instruction for /interact prompt mode",
        examples=["Click the login button"],
    )

    def to_debug_step(self) -> DebugStep:
        return DebugStep(prompt=self.prompt)


class MixedDebugStep(BaseModel):
    """One /interact call — either prompt or code."""

    prompt: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, min_length=1)
    language: InteractLanguage | None = Field(default=None)

    @model_validator(mode="after")
    def require_prompt_or_code(self) -> "MixedDebugStep":
        has_prompt = bool(self.prompt and self.prompt.strip())
        has_code = bool(self.code and self.code.strip())
        if has_prompt == has_code:
            raise ValueError("Provide exactly one of 'prompt' or 'code'")
        return self

    def to_debug_step(self) -> DebugStep:
        lang = self.language.value if self.language else None
        return DebugStep(prompt=self.prompt, code=self.code, language=lang)


class CodeDebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running steps")
    steps: list[CodeDebugStep] = Field(min_length=1)


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


class PromptDebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running steps")
    steps: list[PromptDebugStep] = Field(min_length=1)


class MixedDebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running steps")
    steps: list[MixedDebugStep] = Field(
        min_length=1,
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
    parsed_steps: list[str] | None = Field(
        default=None,
        description="Split step code snippets when the request used code_block",
    )
    step_summaries: list[str] | None = Field(
        default=None,
        description="Human-readable step labels when split with AI",
    )
