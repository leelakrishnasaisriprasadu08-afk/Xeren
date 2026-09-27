# Automation Framework

A small plugin-based module for turning a plain-English request into a
full agent pipeline:

```
your request  ->  understand it  ->  ask permission for what's needed
              ->  gather that data (local files / web)  ->  synthesize
              ->  finished result
```

The exam-prep example from the brief is included as a working plugin:

> "i want to prepare an exam on X, Y subjects"
> 1. figures out the subjects
> 2. asks permission to read your local notes and to search the web
> 3. scans your notes folder for anything matching those subjects
> 4. web-searches for previous exam papers on those subjects
> 5. generates likely questions + model answers
> 6. saves it all as one Markdown study guide

A generic fallback plugin is also included, so anything that doesn't match
a specific automation still goes through the same understand -> permission
-> gather -> synthesize flow, using whatever local/web access it's granted.

## Structure

```
automation_framework/
  config.py                 # settings, all read from environment variables
  core/
    base.py                 # Automation, AutomationContext, AutomationResult, PermissionRequest
    permissions.py           # PermissionManager -- the "ask before accessing" step
    llm_client.py             # thin wrapper around the Anthropic API
    intent_analyzer.py        # free text -> structured intent (domain, subjects, goal...)
    orchestrator.py           # ties intent -> plugin -> permissions -> run together
  tools/
    file_scanner.py          # reads local notes (.txt/.md always, .pdf/.docx if libs installed)
    web_search.py            # pluggable web search (Serper.dev-style JSON API by default)
  plugins/
    exam_prep.py             # the worked example from the brief
    generic_research.py       # catch-all for "whatever else the user wants"
  main.py                    # CLI demo tying it all together
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-...          # required for real intent parsing + generation
export NOTES_DIR=/path/to/your/notes     # folder the framework is allowed to scan
export SEARCH_API_KEY=...                # optional -- enables real web search
export SEARCH_API_URL=...                # optional -- defaults to Serper.dev's endpoint
```

Everything works without the optional keys too -- it just skips that step
and tells you what it would have done, so you can test the plumbing first.

## Run it

```bash
python -m automation_framework.main
```

```
Describe what you want automated (Ctrl+C to quit):
> i want to prepare an exam on Data Structures and Operating Systems

[orchestrator] Understood this as a 'exam_prep' task.
  -> Allow 'local_files'? Reason: to read your class notes/materials on these subjects [y/N]: y
  -> Allow 'web_search'? Reason: to look up previous exam papers for these subjects [y/N]: y

Generated a study guide for Data Structures, Operating Systems at ./automation_outputs/...
Saved to: ./automation_outputs/data_structures_operating_systems_study_guide.md
```

## Adding a new automation

Copy `plugins/generic_research.py` as a starting point and implement the
three required methods:

```python
from automation_framework.core.base import Automation, PermissionRequest, AutomationResult

class MeetingSummaryAutomation(Automation):
    name = "meeting_summary"
    description = "summarize a meeting transcript and list action items"

    def matches(self, intent):
        return intent.get("domain") == "meeting_summary"

    def required_permissions(self, intent):
        return [PermissionRequest("local_files", "to read the transcript file", required=True)]

    def run(self, context):
        # ...read files via LocalFileScanner, call LLMClient, return AutomationResult(...)
        ...
```

Then register it in `main.py`:

```python
orchestrator.register(MeetingSummaryAutomation())
```

No other file needs to change -- the orchestrator, permission flow, and
intent parsing are all generic.

## Swapping pieces out

- **Different LLM provider** -- edit `core/llm_client.py` only.
- **Different search API** (Bing, SerpAPI, Google CSE) -- edit `tools/web_search.py` only.
- **Real permission UI instead of a CLI prompt** -- pass a different
  `prompt_callback` into `PermissionManager` (see `core/permissions.py`).

## Wiring into an existing agent platform

If you're plugging this into a larger agent/RAG system (for example, a
platform with its own tool-execution and planning layers), the
`Automation` classes in `plugins/` are the natural unit to register as
tools/skills on that system -- `matches()` becomes your router's intent
check, and `run()` becomes the tool handler. The permission and
intent-analysis layers can be dropped in as-is or replaced by equivalents
your platform already has.
