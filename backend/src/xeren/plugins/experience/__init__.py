"""Xeren Plugin #8: Experience/Feedback Plugin.

Structured experience and outcome evaluation memory layer enabling task learning, failure
avoidance, user feedback capture, and pattern extraction without modifying model weights.
"""

import sys
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from xeren.plugins.experience.manifest import EXPERIENCE_PLUGIN_MANIFEST
from xeren.plugins.experience.plugin import ExperiencePlugin
from xeren.plugins.experience.registry import ExperienceToolRegistry
from xeren.plugins.experience.schemas import (
    ExperienceInput,
    ExperienceItem,
    ExperienceOperation,
    ExperienceResult,
    ExperienceStats,
    FailureWarning,
    LessonItem,
    OutcomeType,
    UserFeedback,
)
from xeren.plugins.experience.stores.base import BaseExperienceStore
from xeren.plugins.experience.stores.memory import InMemoryExperienceStore
from xeren.plugins.experience.stores.mongo import MongoExperienceStore
from xeren.plugins.experience.tools.feedback import ExperienceFeedbackTool
from xeren.plugins.experience.tools.patterns import ExperiencePatternTool
from xeren.plugins.experience.tools.ranking import ExperienceRankingTool
from xeren.plugins.experience.tools.recorder import ExperienceRecorderTool
from xeren.plugins.experience.tools.retriever import ExperienceRetrieverTool
from xeren.plugins.experience.tools.sanitizer import ExperienceSanitizerTool
from xeren.plugins.experience.workflow import ExperienceWorkflow

__all__ = [
    "ExperiencePlugin",
    "EXPERIENCE_PLUGIN_MANIFEST",
    "ExperienceToolRegistry",
    "ExperienceWorkflow",
    "ExperienceItem",
    "ExperienceInput",
    "ExperienceResult",
    "ExperienceOperation",
    "OutcomeType",
    "UserFeedback",
    "FailureWarning",
    "LessonItem",
    "ExperienceStats",
    "BaseExperienceStore",
    "InMemoryExperienceStore",
    "MongoExperienceStore",
    "ExperienceSanitizerTool",
    "ExperienceRecorderTool",
    "ExperienceRetrieverTool",
    "ExperienceFeedbackTool",
    "ExperienceRankingTool",
    "ExperiencePatternTool",
]


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Ensure src is in sys.path when invoked directly
    src_dir = Path(__file__).resolve().parent.parent.parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console(legacy_windows=False)

    console.print(
        Panel(
            "[bold cyan]⚡ XEREN EXPERIENCE / FEEDBACK PLUGIN (Plugin #8)[/bold cyan]\n"
            "[dim]Autonomous Experience Memory, Pattern Detection & Failure Avoidance[/dim]",
            border_style="cyan",
        )
    )

    # 1. Initialize plugin
    plugin = ExperiencePlugin()
    manifest = plugin.manifest

    table = Table(title="Plugin Manifest", border_style="dim")
    table.add_column("Field", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_row("Name", manifest.name)
    table.add_row("Version", manifest.version)
    table.add_row("Category", manifest.metadata.get("category", "experience_and_feedback"))
    table.add_row("Description", manifest.description)
    table.add_row("Capabilities", ", ".join(manifest.capabilities[:5]) + "...")
    console.print(table)

    # 2. Health Check
    health = plugin.health_check()
    status_style = "bold green" if health.status.value == "healthy" else "bold yellow"
    console.print(f"\n[bold]Health Status:[/bold] [{status_style}]{health.status.value.upper()}[/{status_style}] (latency: {health.latency_ms:.2f}ms)")
    console.print(f"[dim]Persistence store: {health.details.get('store_type', 'SQLite')} ({health.details.get('stored_experiences_count', 0)} records)[/dim]\n")

    # 3. Record Sample Experience
    console.print("[bold cyan]▶ Step 1: Recording an execution outcome...[/bold cyan]")
    rec_res = plugin.workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.EXPERIENCE_RECORD,
            task="Execute zero-downtime database migration",
            plugin_name="data",
            action="schema_migrate",
            success=True,
            lesson="Execute schema changes with explicit safety lock and transactional rollback.",
            metadata={"environment": "production"},
        )
    )
    if rec_res.item:
        console.print(f"[green]✔ Experience recorded successfully![/green] ID: [dim]{rec_res.item.id}[/dim]")
        if rec_res.item.content_fingerprint:
            console.print(f"  Fingerprint: [dim]{rec_res.item.content_fingerprint[:16]}...[/dim]")

    # 4. Extract Distilled Lessons
    console.print("\n[bold cyan]▶ Step 2: Extracting distilled lessons and heuristics...[/bold cyan]")
    lessons_res = plugin.workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.LESSON_EXTRACTION,
            task="Execute zero-downtime database migration",
        )
    )
    if lessons_res.lessons:
        for idx, item in enumerate(lessons_res.lessons[:3], 1):
            console.print(f"  {idx}. [bold white]{item.category}:[/bold white] {item.lesson} [dim](confidence: {item.confidence:.0%})[/dim]")
    else:
        console.print("[dim]No historical lessons recorded yet.[/dim]")

    # 5. Check Failure Avoidance
    console.print("\n[bold cyan]▶ Step 3: Querying failure avoidance advisory...[/bold cyan]")
    avoid_res = plugin.workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.FAILURE_AVOIDANCE,
            task="Delete root system files",
        )
    )
    if avoid_res.failure_warnings:
        for warn in avoid_res.failure_warnings:
            console.print(f"  [bold red]⚠ Warning:[/bold red] {warn.failure_reason}")
            console.print(f"    [yellow]Advice:[/yellow] {warn.avoidance_advice}")
    else:
        console.print("  [dim]No failure risks identified for this task.[/dim]")

    # 6. Outcome Tracking & Stats
    console.print("\n[bold cyan]▶ Step 4: Overall Experience Memory Statistics...[/bold cyan]")
    stats_res = plugin.workflow.run(
        ExperienceInput(
            operation=ExperienceOperation.OUTCOME_TRACKING,
        )
    )
    if stats_res.stats:
        stats = stats_res.stats
        rate = (stats.success_count / stats.total_count * 100) if stats.total_count else 0.0
        console.print(f"  • Total Experiences : [bold cyan]{stats.total_count}[/bold cyan]")
        console.print(f"  • Successful Tasks  : [bold green]{stats.success_count}[/bold green] ({rate:.1f}% success rate)")
        console.print(f"  • Failed Avoidances : [bold red]{stats.failure_count}[/bold red]")
        if stats.plugin_breakdown:
            top_plugins = ", ".join(f"{k}: {v}" for k, v in list(stats.plugin_breakdown.items())[:4])
            console.print(f"  • Top Plugins       : [dim]{top_plugins}[/dim]")

    console.print("\n[bold green]✔ Experience Plugin execution cycle completed successfully![/bold green]\n")

