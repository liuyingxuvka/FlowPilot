from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unlink_with_windows_retry(path: Path, *, attempts: int = 20, delay: float = 0.02) -> None:
    for attempt in range(attempts):
        try:
            path.unlink()
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(delay)
