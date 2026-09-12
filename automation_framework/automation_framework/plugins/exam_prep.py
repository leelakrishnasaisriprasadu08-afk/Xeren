"""
The exact workflow from the brief, as a plugin:

    "i want to prepare an exam on X, Y subjects"
        -> understand the subjects
        -> ask permission to read local files/notes and to search the web
        -> scan the user's notes for X, Y
        -> search the web for previous exam papers on X, Y
        -> generate likely questions + model answers
        -> save it all as one study guide
"""
import os
from typing import Any, Dict, List

from ..config import settings
from ..core.base import Automation, AutomationContext, AutomationResult, PermissionRequest
from ..core.llm_client import LLMClient
from ..tools.file_scanner import LocalFileScanner
from ..tools.web_search import WebSearchTool

_QNA_PROMPT = """You are helping a student prepare for an exam on: {subjects}.

Notes and materials found on their device:
{local_notes}

Findings from previous exam papers / web search:
{web_notes}

Using the above (plus solid general knowledge of these subjects), produce:
1. A short list of the topics most likely to be tested, ranked by importance.
2. 10-15 likely exam questions spanning those topics.
3. A model answer for each question -- concise and exam-ready, not padded.

Format the whole thing as clean Markdown with headings.
"""


class ExamPrepAutomation(Automation):
    name = "exam_prep"
    description = "scan your notes + past papers and generate likely exam questions & answers"

    def matches(self, intent: Dict[str, Any]) -> bool:
        return intent.get("domain") == "exam_prep"

    def required_permissions(self, intent: Dict[str, Any]) -> List[PermissionRequest]:
        return [
            PermissionRequest(
                "local_files",
                "to read your class notes/materials on these subjects",
                required=False,
            ),
            PermissionRequest(
                "web_search",
                "to look up previous exam papers for these subjects",
                required=False,
            ),
        ]

    def run(self, context: AutomationContext) -> AutomationResult:
        subjects: List[str] = context.intent.get("subjects") or []
        if not subjects:
            subjects = [context.intent.get("goal", context.user_text)]

        local_notes = "(no local file access granted)"
        if context.has("local_files"):
            scanner = LocalFileScanner(settings.notes_dir)
            files = scanner.find_by_keywords(subjects)
            local_notes = scanner.extract_text(files) or "(no matching notes found)"

        web_notes = "(no web access granted)"
        if context.has("web_search"):
            search = WebSearchTool()
            all_results = []
            for subject in subjects:
                all_results += search.search(f"{subject} previous exam papers questions")
            web_notes = search.summarize_results(all_results) or "(no results found)"

        llm = LLMClient()
        if llm.available():
            report = llm.complete(
                _QNA_PROMPT.format(
                    subjects=", ".join(subjects),
                    local_notes=local_notes,
                    web_notes=web_notes,
                ),
                max_tokens=3000,
            )
        else:
            report = (
                "# LLM not configured\n\n"
                "Set ANTHROPIC_API_KEY to generate the actual question set.\n\n"
                f"Subjects detected: {', '.join(subjects)}\n\n"
                f"## Local notes found\n{local_notes}\n\n## Web findings\n{web_notes}"
            )

        os.makedirs(settings.output_dir, exist_ok=True)
        safe_name = ("_".join(subjects[:3]).replace(" ", "_").lower() or "exam_prep")[:60]
        out_path = os.path.join(settings.output_dir, f"{safe_name}_study_guide.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)

        return AutomationResult(
            summary=f"Generated a study guide for {', '.join(subjects)} at {out_path}",
            details={"subjects": subjects},
            output_files=[out_path],
        )
