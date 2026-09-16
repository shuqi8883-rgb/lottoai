#!/usr/bin/env python3
"""Build a compact job index for the GitHub Pages job radar.

The daily collector keeps rich job records. This step creates a lightweight
index for fast browser/mobile loading and splits full records into chunks.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "jobs" / "data"
SOURCE = DATA / "jobs.json"
INDEX = DATA / "jobs-index.json"
CHUNKS = DATA / "jobs-chunks"
CHUNK_SIZE = 5000


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source: {SOURCE}")
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("jobs.json must contain a JSON array")

    def compact(job: dict) -> dict:
        return {
            "id": job.get("id"),
            "company": job.get("company") or job.get("company_name"),
            "title": job.get("title"),
            "location": job.get("location"),
            "level": job.get("level"),
            "major": job.get("major") or job.get("major_tags") or [],
            "source": job.get("source"),
            "updated_at": job.get("updated_at") or job.get("date_posted"),
            "url": job.get("url") or job.get("apply_url"),
        }

    compacted = [compact(x) for x in records]
    compacted.sort(key=lambda x: x.get("updated_at") or "", reverse=True)

    INDEX.write_text(json.dumps(compacted, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    CHUNKS.mkdir(parents=True, exist_ok=True)
    for old in CHUNKS.glob("jobs-*.json"):
        old.unlink()
    for i in range(0, len(records), CHUNK_SIZE):
        chunk_no = i // CHUNK_SIZE + 1
        path = CHUNKS / f"jobs-{chunk_no:04d}.json"
        path.write_text(json.dumps(records[i:i + CHUNK_SIZE], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    meta_path = DATA / "update-meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.update({
        "compact_index": "jobs-index.json",
        "chunk_dir": "jobs-chunks",
        "chunk_size": CHUNK_SIZE,
        "chunk_count": (len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE,
        "index_count": len(compacted),
        "compacted_at": datetime.now(timezone.utc).isoformat(),
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {INDEX} ({len(compacted)} records)")
    print(f"Wrote {(len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE} chunks")


if __name__ == "__main__":
    main()
