# evaluator.py — second LLM call to score the quality of generated test cases.
#
# Using a cheaper model (gpt-4o-mini by default) keeps the cost low while still
# catching obviously bad output like vague steps or missing preconditions.
#
# Env vars: JUDGE_PROVIDER, JUDGE_MODEL (defaults: openai, gpt-4o-mini)

from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

# gpt-4o-mini is cheap enough that scoring every run doesn't hurt the bill much
_JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", "openai")
_JUDGE_MODEL    = os.getenv("JUDGE_MODEL", "gpt-4o-mini")
_JUDGE_KEY_ENV  = "OPENAI_API_KEY"

_JUDGE_SYSTEM_PROMPT = """\
You are a senior QA engineering manager reviewing AI-generated test cases.
Your job is to evaluate each test case on four criteria and assign a score.

Scoring rubric (1 = very poor, 5 = excellent):
  specificity   : Are the test steps concrete and executable by any QA engineer?
  coverage      : Does the test case actually address the stated gap_reason?
  completeness  : Are preconditions, steps, and expected result all clearly stated?
  actionability : Can the test be run without guessing or asking follow-up questions?

Return ONLY valid JSON — a list of evaluation objects.
Each object must have EXACTLY these keys:
  tc_number    : string matching the input tc_number
  specificity  : integer 1-5
  coverage     : integer 1-5
  completeness : integer 1-5
  actionability: integer 1-5
  composite    : float, mean of the four scores, rounded to 2 decimal places
  notes        : one sentence explaining the main weakness (or "None" if excellent)

Do not include any text outside the JSON array.
"""

_JUDGE_USER_TEMPLATE = """\
Bug summary: {summary}

Evaluate the following {n} test cases:

{test_cases_json}
"""


# ---------------------------------------------------------------------------
# Grade bands
# ---------------------------------------------------------------------------

def _grade(score: float) -> str:
    if score >= 4.5:
        return "Excellent"
    if score >= 3.5:
        return "Good"
    if score >= 2.5:
        return "Adequate"
    return "Poor"


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class TestCaseEvaluator:
    """Scores generated test cases using a second (judge) LLM call.

    Intentionally uses a different model from the generator to reduce
    self-confirmation bias.
    """

    def __init__(
        self,
        provider: str | None = None,
        api_key:  str | None = None,
        model:    str | None = None,
    ) -> None:
        self.provider = (provider or _JUDGE_PROVIDER).lower()
        self.api_key  = api_key or os.getenv(_JUDGE_KEY_ENV, "")
        self.model    = model or _JUDGE_MODEL

    def evaluate(self, test_cases: list[dict], issue_summary: str = "") -> list[dict]:
        """Score each test case and return the list with quality_* fields attached.
        Falls back to original list if scoring fails — never blocks analysis.
        """
        if not test_cases:
            return test_cases
        if self.provider == "mock" or not self.api_key:
            return self._mock_evaluate(test_cases)

        try:
            raw = self._call_judge(test_cases, issue_summary)
            scores = self._parse_scores(raw)
            return self._merge(test_cases, scores)
        except Exception as exc:
            log.warning("TestCaseEvaluator: evaluation failed: %s", exc)
            return test_cases

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_judge(self, test_cases: list[dict], summary: str) -> str:
        # Trim to essentials so the judge prompt stays small
        slim = [
            {k: tc.get(k, "") for k in
             ("tc_number", "title", "gap_reason", "steps", "expected", "preconditions")}
            for tc in test_cases
        ]
        user_prompt = _JUDGE_USER_TEMPLATE.format(
            summary=summary[:300] or "(no summary provided)",
            n=len(slim),
            test_cases_json=json.dumps(slim, indent=2),
        )

        if self.provider in ("openai", "netapp"):
            return self._call_openai_judge(user_prompt)
        if self.provider == "anthropic":
            return self._call_anthropic_judge(user_prompt)
        if self.provider == "gemini":
            return self._call_gemini_judge(user_prompt)
        return self._mock_raw(test_cases)

    def _call_openai_judge(self, user_prompt: str) -> str:
        import openai  # noqa: PLC0415
        from llm_agent import PROVIDERS  # noqa: PLC0415
        cfg    = PROVIDERS.get(self.provider, {})
        kwargs: dict = {"api_key": self.api_key}
        if cfg.get("base_url"):
            kwargs["base_url"] = cfg["base_url"]
        client = openai.OpenAI(**kwargs)
        resp   = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,   # deterministic scoring
        )
        return resp.choices[0].message.content

    def _call_anthropic_judge(self, user_prompt: str) -> str:
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=self.api_key)
        msg    = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=_JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return msg.content[0].text

    def _call_gemini_judge(self, user_prompt: str) -> str:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=self.api_key)
        llm  = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=_JUDGE_SYSTEM_PROMPT,
        )
        resp = llm.generate_content(user_prompt,
                                    generation_config={"temperature": 0.0})
        return resp.text

    # ------------------------------------------------------------------
    # Parse & merge
    # ------------------------------------------------------------------

    def _parse_scores(self, raw: str) -> dict[str, dict]:
        """Parse judge response into {tc_number: scores_dict}."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text  = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        return {item["tc_number"]: item for item in data if "tc_number" in item}

    def _merge(self, test_cases: list[dict], scores: dict[str, dict]) -> list[dict]:
        result = []
        for tc in test_cases:
            tc_copy = dict(tc)
            score_data = scores.get(tc.get("tc_number", ""))
            if score_data:
                composite = score_data.get("composite", 0.0)
                tc_copy["quality_score"] = round(float(composite), 2)
                tc_copy["quality_grade"] = _grade(composite)
                tc_copy["quality_notes"] = score_data.get("notes", "")
            result.append(tc_copy)
        return result

    # ------------------------------------------------------------------
    # Mock evaluation (for development / no API key)
    # ------------------------------------------------------------------

    def _mock_evaluate(self, test_cases: list[dict]) -> list[dict]:
        result = []
        for i, tc in enumerate(test_cases):
            score = 4.0 - (i % 3) * 0.25   # vary scores slightly
            result.append({
                **tc,
                "quality_score": round(score, 2),
                "quality_grade": _grade(score),
                "quality_notes": "Mock evaluation — no judge API key configured.",
            })
        return result

    def _mock_raw(self, test_cases: list[dict]) -> str:
        return json.dumps([
            {
                "tc_number":    tc.get("tc_number", "TC-001"),
                "specificity":  4, "coverage": 4,
                "completeness": 4, "actionability": 4,
                "composite":    4.0,
                "notes":        "Mock judge — configure JUDGE_PROVIDER and key.",
            }
            for tc in test_cases
        ])
