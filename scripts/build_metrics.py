"""Build and publish the Umiya Screener analytical dataset.

Run this from the repository root on a scheduled data worker/cron job,
not from the web/API process.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.service import build_metric_frame, write_metric_cache  # noqa: E402


if __name__ == "__main__":
    frame, built_at = build_metric_frame()
    write_metric_cache(frame, built_at)
    print(f"Published {len(frame):,} stocks to the screener cache at {built_at.isoformat()}")
