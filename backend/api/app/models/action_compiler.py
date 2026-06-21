"""Models for compiling scrape actions into /interact steps."""

from pydantic import BaseModel, Field

from app.models.schemas import InteractLanguage


class ActionsCompileError(ValueError):
    """Raised when a scrape actions array cannot be compiled."""


class ActionCompileStep(BaseModel):
    code: str = Field(description="Prepared code for one /interact call")
    summary: str = Field(description="Human-readable label for this step")


class ActionCompileResult(BaseModel):
    language: InteractLanguage
    steps: list[ActionCompileStep] = Field(min_length=1)

    @property
    def codes(self) -> list[str]:
        return [step.code for step in self.steps]

    @property
    def summaries(self) -> list[str]:
        return [step.summary for step in self.steps]
