"""Models for splitting code blocks into /interact steps."""

from pydantic import BaseModel, Field

from app.models.schemas import InteractLanguage


class CodeSplitError(ValueError):
    """Raised when a code block cannot be split."""


class CodeSplitStepOut(BaseModel):
    code: str = Field(
        description="Standalone code executed in one /interact call",
    )
    summary: str = Field(
        description="Short human-readable label for this step (shown in debug reports)",
        max_length=120,
    )


class CodeSplitPlan(BaseModel):
    steps: list[CodeSplitStepOut] = Field(
        min_length=1,
        description="Ordered list of /interact code steps",
    )


class CodeSplitStep(BaseModel):
    code: str = Field(description="Prepared code for one /interact call")
    summary: str = Field(description="Human-readable label for this step")


class CodeSplitResult(BaseModel):
    language: InteractLanguage
    steps: list[CodeSplitStep] = Field(
        min_length=1,
        description="Ordered steps ready to run via /interact",
    )

    @property
    def codes(self) -> list[str]:
        return [step.code for step in self.steps]

    @property
    def summaries(self) -> list[str]:
        return [step.summary for step in self.steps]


class AnthropicNotConfiguredError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is not set."""
