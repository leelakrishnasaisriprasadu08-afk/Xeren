"""
Turns free text like:
    "i want to prepare for my DBMS and OS exam next week"
into a structured intent dict the orchestrator can route on:
    {
      "domain": "exam_prep",
      "subjects": ["DBMS", "OS"],
      "goal": "prepare for the upcoming exam",
      "needs_local_files": true,
      "needs_web_search": true
    }

Falls back to a simple keyword guess if no LLM key is configured, so the
plumbing is still testable without an API key.
"""
from typing import Any, Dict

from .llm_client import LLMClient

_INTENT_PROMPT = """A user typed the following request to an automation assistant:

\"\"\"{user_text}\"\"\"

Work out what they want. Return JSON with this exact shape:
{{
  "domain": "<short tag such as exam_prep, meeting_summary, code_review, research, other>",
  "subjects": ["<topic 1>", "<topic 2>", ...],
  "goal": "<one sentence describing the end goal>",
  "needs_local_files": <true/false -- true if their own notes/documents would help>,
  "needs_web_search": <true/false -- true if current/external info would help>
}}
"""


class IntentAnalyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, user_text: str) -> Dict[str, Any]:
        if self.llm.available():
            intent = self.llm.complete_json(_INTENT_PROMPT.format(user_text=user_text))
            if intent:
                return intent
        return self._fallback(user_text)

    @staticmethod
    def _fallback(user_text: str) -> Dict[str, Any]:
        """Crude keyword guess, used only when no LLM key is configured."""
        text = user_text.lower()
        domain = "other"
        if any(w in text for w in ("exam", "test", "crack", "quiz")):
            domain = "exam_prep"
        return {
            "domain": domain,
            "subjects": [],
            "goal": user_text.strip(),
            "needs_local_files": any(w in text for w in ("notes", "files", "material")),
            "needs_web_search": True,
        }
