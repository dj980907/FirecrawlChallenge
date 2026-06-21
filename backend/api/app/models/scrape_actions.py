"""API request models for scrape actions debug (Firecrawl SDK action types)."""

from typing import Annotated, Union

from firecrawl.v2.types import (
    ClickAction,
    ExecuteJavascriptAction,
    PDFAction,
    PressAction,
    ScrapeAction as ScrapeCaptureAction,
    ScreenshotAction,
    ScrollAction,
    WaitAction,
    WriteAction,
)
from pydantic import BaseModel, Field, HttpUrl

from app.models.schemas import InteractLanguage

FirecrawlAction = Annotated[
    Union[
        WaitAction,
        ScreenshotAction,
        ClickAction,
        WriteAction,
        PressAction,
        ScrollAction,
        ScrapeCaptureAction,
        ExecuteJavascriptAction,
        PDFAction,
    ],
    Field(discriminator="type"),
]

__all__ = [
    "ActionsDebugRunRequest",
    "ClickAction",
    "ExecuteJavascriptAction",
    "FirecrawlAction",
    "PDFAction",
    "PressAction",
    "ScrapeCaptureAction",
    "ScreenshotAction",
    "ScrollAction",
    "WaitAction",
    "WriteAction",
]


class ActionsDebugRunRequest(BaseModel):
    url: HttpUrl = Field(description="Page URL to open before running actions")
    actions: list[FirecrawlAction] = Field(
        min_length=1,
        description="Firecrawl scrape actions array, one step per action",
    )
    language: InteractLanguage = Field(
        default=InteractLanguage.NODE,
        description="Target /interact language for compiled steps: node, python, or bash",
    )
