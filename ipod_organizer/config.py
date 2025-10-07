"""Shared configuration for ipod_organizer."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(os.environ.get("IPOD_ORGANIZER_HOME", Path.home() / ".ipod_organizer")).expanduser()
LIBRARY_DB = APP_DIR / "library.db"
LOG_FILE = APP_DIR / "ipod_organizer.log"


def ensure_app_dirs() -> None:
    """Ensure the application directory exists."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
