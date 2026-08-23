#!/usr/bin/env python3
"""Run the scheduled Google Drive ingest without starting formal training."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


def main() -> int:
    remote = os.getenv("SOP_GOOGLE_SOURCE", "").strip()
    if not remote:
        print("Google Drive ingest skipped: SOP_GOOGLE_SOURCE is not configured", file=sys.stderr)
        return 2
    job_id = f"DAILY-{time.strftime('%Y%m%d-%H%M%S')}"
    server.CLOUD_SYNC_JOBS[job_id] = {
        "job_id": job_id,
        "action": "pull_google",
        "operator": "systemd-timer",
        "status": "queued",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    server.run_cloud_sync_job(job_id, "pull_google")
    result = server.CLOUD_SYNC_JOBS[job_id]
    print(json.dumps(result, ensure_ascii=False))
    if result.get("status") != "completed":
        return 1
    print("Ingest completed. Formal training remains blocked until Reviewer acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
