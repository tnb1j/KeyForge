"""Anti-Clock-Rollback Monotonic State Tracker."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class ClockGuard:
    """Detects backwards system clock manipulation by recording trusted timestamps."""

    def __init__(self, state_file: Path | None = None) -> None:
        if state_file is None:
            state_file = Path.home() / ".keyforge" / ".clock_guard"
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def check_and_update(self, now: datetime | None = None) -> bool:
        """Check if the current time is at or after the last recorded trusted time.

        Returns:
            bool: True if clock is valid (monotonic), False if rollback detected.
        """
        current_dt = now or datetime.now(timezone.utc)
        current_ts = current_dt.timestamp()

        last_known_ts = 0.0
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                last_known_ts = float(data.get("last_timestamp", 0.0))
            except Exception:
                last_known_ts = 0.0

        # Allow 60 second clock drift tolerance
        if current_ts < (last_known_ts - 60.0):
            return False  # Clock rolled backwards!

        # Update last known timestamp
        try:
            state = {
                "last_timestamp": current_ts,
                "last_iso": current_dt.isoformat(),
            }
            self.state_file.write_text(json.dumps(state), encoding="utf-8")
        except Exception:
            pass

        return True
