#!/usr/bin/env python3
"""Read public Hits statistics without incrementing counters.

Individual article pages load the SVG badge to count page views. This script
only reads the statistics API and writes a shared snapshot for the home page.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://hits.sh/api/urns/ssy671.github.io/dogu-life-preview/post/"
USER_AGENT = (
    "DoguLifeViewSync/1.0 (+https://ssy671.github.io/dogu-life-preview/)"
)
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _count(value: object) -> int:
    # JSON booleans are Python ints, but they are not valid view counts.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("View counts must be nonnegative integers")
    return value


def fetch_count(slug: str, opener=urlopen) -> int:
    """Return total requests counted for a slug; an unseen counter is zero.

    The /api/urns/ endpoint is read-only. Never replace it with the SVG endpoint:
    fetching the SVG would increment the counter during every scheduled sync.
    The default TLS certificate checks provided by urllib remain enabled.
    """
    if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("Invalid article slug")
    request = Request(
        API_BASE + slug,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener(request, timeout=10) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return 0
        raise
    if not isinstance(payload, dict) or "total" not in payload:
        raise ValueError("Statistics response is missing total")
    return _count(payload["total"])


def _read_snapshot(path: Path) -> dict:
    if not path.exists():
        return {"updated_at": None, "counts": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("counts"), dict):
        raise ValueError("View snapshot must contain a counts object")
    for value in data["counts"].values():
        _count(value)
    return {"updated_at": data.get("updated_at"), "counts": dict(data["counts"])}


def _write_snapshot(path: Path, snapshot: dict) -> None:
    """Replace the snapshot atomically, keeping the previous file on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sync(posts_path=None, views_path=None, *, opener=urlopen, now=None) -> dict:
    """Refresh published article counts, retaining old data on API failures.

    A failed request never replaces an existing value. Even a successful zero
    or a 404 cannot erase a previously counted view. No successful responses
    means no updated timestamp and no file write. Unchanged totals also retain
    the original timestamp and bytes. Other stored slugs survive.
    """
    posts_path = Path(posts_path) if posts_path is not None else ROOT / "content/posts.json"
    views_path = Path(views_path) if views_path is not None else ROOT / "content/views.json"
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    if not isinstance(posts, list):
        raise ValueError("Published posts must be a JSON array")
    slugs = []
    for post in posts:
        slug = post.get("slug") if isinstance(post, dict) else None
        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Published post is missing a valid slug")
        if slug not in slugs:
            slugs.append(slug)
    snapshot = _read_snapshot(views_path)
    original_counts = dict(snapshot['counts'])
    refreshed = 0
    errors = 0
    if slugs:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(fetch_count, slug, opener): slug for slug in slugs}
            for future in as_completed(futures):
                slug = futures[future]
                try:
                    count = future.result()
                except (URLError, OSError, ValueError):
                    errors += 1
                    continue
                snapshot["counts"][slug] = max(snapshot["counts"].get(slug, 0), count)
                refreshed += 1
    changed = snapshot['counts'] != original_counts
    if refreshed and (changed or not views_path.exists()):
        timestamp = now if now is not None else datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Snapshot timestamp must include a timezone")
        snapshot["updated_at"] = timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        _write_snapshot(views_path, snapshot)
    print(
        f"View sync: {len(slugs)} articles, {refreshed} API responses, "
        f"{errors} errors; "
        + ("snapshot updated." if changed else "counts unchanged; previous snapshot retained.")
    )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=Path, default=ROOT / "content/posts.json")
    parser.add_argument("--views", type=Path, default=ROOT / "content/views.json")
    args = parser.parse_args()
    sync(args.posts, args.views)


if __name__ == "__main__":
    main()
