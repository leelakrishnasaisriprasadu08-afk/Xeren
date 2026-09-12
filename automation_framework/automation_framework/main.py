"""
Command-line demo of the automation framework.

Run it, describe what you want ("i want to prepare an exam on DBMS and OS"),
answer the permission prompts, and it runs the full pipeline end to end.

    $ export ANTHROPIC_API_KEY=sk-...
    $ export NOTES_DIR=/path/to/your/notes
    $ python -m automation_framework.main
"""
from automation_framework.core.orchestrator import Orchestrator
from automation_framework.plugins.exam_prep import ExamPrepAutomation
from automation_framework.plugins.generic_research import GenericResearchAutomation


def build_orchestrator() -> Orchestrator:
    orchestrator = Orchestrator()
    orchestrator.register(ExamPrepAutomation())
    orchestrator.register(GenericResearchAutomation())  # keep this one registered last
    return orchestrator


def main():
    orchestrator = build_orchestrator()
    print("Describe what you want automated (Ctrl+C to quit):")
    while True:
        try:
            user_text = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_text:
            continue
        result = orchestrator.handle(user_text)
        print("\n" + result.summary)
        if result.output_files:
            print("Saved to:", ", ".join(result.output_files))


if __name__ == "__main__":
    main()
