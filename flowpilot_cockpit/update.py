"""Lightweight update check for the FlowPilot cockpit."""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

from . import __version__


RELEASES_URL = "https://github.com/liuyingxuvka/FlowPilot/releases"
LATEST_RELEASE_API_URL = "https://api.github.com/repos/liuyingxuvka/FlowPilot/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str | None = None
    release_url: str = RELEASES_URL
    error: str | None = None

    @property
    def has_update(self) -> bool:
        return self.latest_version is not None and compare_versions(self.latest_version, self.current_version) > 0


def _version_parts(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+){0,3})", value)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def compare_versions(left: str, right: str) -> int:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    size = max(len(left_parts), len(right_parts))
    left_padded = left_parts + (0,) * (size - len(left_parts))
    right_padded = right_parts + (0,) * (size - len(right_parts))
    return (left_padded > right_padded) - (left_padded < right_padded)


def check_latest_release(timeout: float = 3.0) -> UpdateInfo:
    request = urllib.request.Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "FlowPilot-Cockpit",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return UpdateInfo(current_version=__version__, error=str(exc))

    latest = str(payload.get("tag_name") or payload.get("name") or "").strip() or None
    url = str(payload.get("html_url") or RELEASES_URL)
    return UpdateInfo(current_version=__version__, latest_version=latest, release_url=url)
