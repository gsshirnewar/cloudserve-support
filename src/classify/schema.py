"""Pydantic schemas for classification outputs (T19, P-CLS-001)."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClassificationAlternative(BaseModel):
    intent: str
    urgency: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class ClassificationPromptOutput(BaseModel):
    """Structured JSON output expected from P-CLS-001."""

    model_config = ConfigDict(extra="allow")

    prompt_id: str = "P-CLS-001"
    prompt_version: str = "v1.0.0"
    ticket_id: str
    intent: str
    intent_confidence: float = Field(ge=0.0, le=1.0)
    urgency: str
    urgency_confidence: float = Field(ge=0.0, le=1.0)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    alternatives: List[ClassificationAlternative] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    notes_for_routing: str = ""

    @field_validator("intent_confidence", "urgency_confidence", "overall_confidence", mode="before")
    @classmethod
    def _clamp_conf(cls, v):
        try:
            f = float(v)
        except Exception:
            return 0.0
        return max(0.0, min(1.0, f))
