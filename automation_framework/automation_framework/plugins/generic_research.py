"""
Catch-all automation for anything that doesn't match a more specific
plugin -- this is the "also automate whatever else the user wants" piece.
It follows the same shape (understand -> ask permission -> gather ->
synthesize) with no domain-specific logic, so it also doubles as the
template to copy when writing a new specific plugin.
"""
from typing import Any, Dict, List

from ..config import settings
from ..core.base import Automation, AutomationContext, AutomationResult, PermissionRequest
from ..core.llm_client import LLMClient
from ..tools.file_scanner import LocalFileScanner
from ..tools.web_search import WebSearchTool

_GENERIC_PROMPT = """A user asked an automation assistant for help with this:

\"\"\"{user_text}\"\"\"

Relevant local material found:
{local_notes}

Relevant web findings:
{web_notes}

Do the task described above as completely as you can, using the material
above where useful. Reply directly with the finished output, not a plan
for how you'd do it.
"""


class GenericResearchAutomation(Automation):
    name = "generic_research"
    description = "general-purpose fallback: gathers your files/web info and completes the task"

    def matches(self, intent: Dict[str, Any]) -> bool:
        return True  # always able to at least attempt it -- register this one last

    def required_permissions(self, intent: Dict[str, Any]) -> List[PermissionRequest]:
        reqs = []
        if intent.get("needs_local_files"):
            reqs.append(PermissionRequest("local_files", "to use your relevant files", required=False))
        if intent.get("needs_web_search"):
            reqs.append(PermissionRequest("web_search", "to look up current/external info", required=False))
        return reqs

    def run(self, context: AutomationContext) -> AutomationResult:
        local_notes = "(not used)"
        if context.has("local_files"):
            scanner = LocalFileScanner(settings.notes_dir)
            keywords = context.intent.get("subjects") or []
            files = scanner.find_by_keywords(keywords)
            local_notes = scanner.extract_text(files) or "(no matching files found)"

        web_notes = "(not used)"
        if context.has("web_search"):
            search = WebSearchTool()
            results = search.search(context.intent.get("goal", context.user_text))
            web_notes = search.summarize_results(results) or "(no results found)"

        llm = LLMClient()
        if llm.available():
            output = llm.complete(
                _GENERIC_PROMPT.format(
                    user_text=context.user_text, local_notes=local_notes, web_notes=web_notes
                ),
                max_tokens=2000,
            )
        else:
            output = "LLM not configured -- set ANTHROPIC_API_KEY to get real output here."

        return AutomationResult(summary=output)
