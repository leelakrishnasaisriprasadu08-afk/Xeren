"""
Asks the user for permission before an automation touches anything
sensitive (local files, media, web access, etc), exactly like the
"allow access to files and media" step in the brief.

The default implementation asks on the command line. Swap `prompt_callback`
for a GUI/web dialog (a real permission popup, a Slack button, whatever)
and nothing else in the framework has to change -- that's the whole point
of keeping this separate from the plugins themselves.
"""
from typing import Callable, Dict, List

from .base import PermissionRequest


def _cli_prompt(request: PermissionRequest) -> bool:
    answer = input(
        f"  -> Allow '{request.key}'? Reason: {request.reason} [y/N]: "
    ).strip().lower()
    return answer in ("y", "yes")


class PermissionManager:
    def __init__(self, prompt_callback: Callable[[PermissionRequest], bool] = _cli_prompt):
        self._prompt = prompt_callback
        self._granted_cache: Dict[str, bool] = {}

    def request(self, requests: List[PermissionRequest]) -> Dict[str, bool]:
        """Ask (once per key, then cached) for each requested permission.
        Returns a {key: granted} map. A denied-but-required permission is
        still returned as False -- it's the plugin's job to decide whether
        it can degrade gracefully or must stop."""
        results: Dict[str, bool] = {}
        for req in requests:
            if req.key in self._granted_cache:
                results[req.key] = self._granted_cache[req.key]
                continue
            granted = self._prompt(req)
            self._granted_cache[req.key] = granted
            results[req.key] = granted
        return results

    def revoke(self, key: str) -> None:
        self._granted_cache.pop(key, None)
