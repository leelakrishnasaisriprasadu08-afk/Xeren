"""
Central configuration for the automation framework.

Reads sensitive values (API keys, folder paths) from environment variables
so nothing needs to be hard-coded into source files or committed to git.
"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # Any web-search backend that returns JSON results can be plugged in
    # here. Serper.dev / SerpAPI / Bing Web Search all work with a small
    # adapter change in tools/web_search.py.
    search_api_key: str = os.getenv("SEARCH_API_KEY", "")
    search_api_url: str = os.getenv("SEARCH_API_URL", "https://google.serper.dev/search")

    # Root folder the framework is allowed to scan for local notes/materials.
    # Point this at wherever the user's class notes actually live.
    notes_dir: str = os.getenv("NOTES_DIR", os.path.expanduser("~/notes"))

    # Where generated reports (e.g. exam study guides) get written.
    output_dir: str = os.getenv("AUTOMATION_OUTPUT_DIR", "./automation_outputs")


settings = Settings()
