# models.py — Pydantic schemas for BugBuddy test case output and user feedback.
# Keeping this separate from llm_agent.py so the evaluator and app can both
# import the types without circular deps.

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, ValidationError


# TODO: add "Usability" and "Compatibility" once QE team agrees on taxonomy
class TestType(str, Enum):
    FUNCTIONAL  = "Functional"
    REGRESSION  = "Regression"
    NEGATIVE    = "Negative"
    PERFORMANCE = "Performance"
    BOUNDARY    = "Boundary"
    SECURITY    = "Security"
    INTEGRATION = "Integration"


class QualityGrade(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    ADEQUATE = "Adequate"
    POOR = "Poor"


# ---------------------------------------------------------------------------
# Core TestCase model
# ---------------------------------------------------------------------------

class TestCase(BaseModel):
    """Single generated test case. Validated on the way out of the LLM call."""
    tc_number:     str       = Field(..., pattern=r"^TC-\d{3,}$",
                                     description="e.g. TC-001")
    title:         str       = Field(..., min_length=5, max_length=200)
    gap_reason:    str       = Field(..., min_length=10,
                                     description="Why this test was missing")
    preconditions: str       = Field(default="None",
                                     description="Required state before running the test")
    steps:         list[str] = Field(..., min_length=1,
                                     description="Ordered action steps")
    expected:      str       = Field(..., min_length=10,
                                     description="Observable result that would have caught the bug")
    test_type:     TestType  = Field(..., description="Category of the test case")

    # Optional fields added by the evaluator (LLM-as-Judge)
    quality_score: float | None         = Field(default=None, ge=0.0, le=5.0)
    quality_grade: QualityGrade | None  = Field(default=None)
    quality_notes: str | None           = Field(default=None)

    @field_validator("tc_number", mode="before")
    @classmethod
    def normalise_tc_number(cls, v: Any) -> str:
        """Accept 'TC-1' and normalise to 'TC-001'."""
        v = str(v).strip()
        if v.upper().startswith("TC-"):
            num = v[3:].lstrip("0") or "0"
            return f"TC-{int(num):03d}"
        return v

    @field_validator("steps", mode="before")
    @classmethod
    def coerce_steps(cls, v: Any) -> list[str]:
        """Accept a single string as a one-item list."""
        if isinstance(v, str):
            return [v]
        return v

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


def parse_llm_output(raw_json: str, issue_key: str = "UNKNOWN") -> list[TestCase]:
    """Parse and validate the JSON blob returned by the LLM.

    Handles markdown fences, single-dict responses, and partial validation
    failures (bad items are skipped rather than crashing the whole run).
    """
    import logging
    log = logging.getLogger(__name__)

    # Strip markdown code fences
    text = raw_json.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text  = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("[%s] LLM returned invalid JSON: %s", issue_key, exc)
        return []

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        log.error("[%s] LLM output is not a list or dict: %r", issue_key, type(data))
        return []

    results: list[TestCase] = []
    for i, item in enumerate(data):
        try:
            results.append(TestCase.model_validate(item))
        except ValidationError as exc:
            log.warning("[%s] TC item %d failed validation: %s", issue_key, i, exc)
    return results


class TestCaseFeedback(BaseModel):
    """Feedback submitted via /api/feedback — stored back to ChromaDB metadata."""
    issue_key:  str
    tc_number:  str
    rating:     int   = Field(..., ge=1, le=5,
                              description="1=useless … 5=perfect")
    comment:    str   = Field(default="")
    provider:   str   = Field(default="unknown")
    model:      str   = Field(default="unknown")
