"""Fail a run that leaves a missing or inconsistent daily publication."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo('Asia/Seoul')


def publication_health(root=ROOT, now=None):
    """Inspect local publication results without changing articles or the queue."""
    root = Path(root)
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    read = lambda name: json.loads((root / 'content' / name).read_text(encoding='utf-8'))
    posts, queue, state = (read(name) for name in ('posts.json', 'queue.json', 'state.json'))
    today = now.date().isoformat()
    count = sum(datetime.fromisoformat(p['published_at']).astimezone(KST).date()
                == now.date() for p in posts)
    hour = int(state.get('publish_hour', 9))
    last = state.get('last_release_date', '')
    reason = 'published_today'
    if int(state.get('daily_limit', 3)) != 3:
        reason = 'invalid_daily_limit'
    elif len({p['slug'] for p in posts}) != len(posts):
        reason = 'duplicate_published_slugs'
    elif last > today:
        reason = 'future_release_date'
    elif count > 3:
        reason = 'too_many_articles_today'
    elif count in (1, 2):
        reason = 'partial_publication'
    elif count == 3 and last != today:
        reason = 'release_date_mismatch'
    elif count == 0 and last == today:
        reason = 'release_date_without_articles'
    elif count == 0:
        reason = 'before_publication_hour' if now.hour < hour else 'missing_publication'
    return {
        'ok': reason in ('published_today', 'before_publication_hour'),
        'reason': reason,
        'checked_at': now.isoformat(),
        'date': today,
        'publish_hour': hour,
        'last_release_date': last,
        'today_count': count,
        'remaining': len(queue),
    }


def main():
    result = publication_health()
    result['event'] = os.environ.get('PUBLICATION_EVENT', 'local')
    result['schedule'] = os.environ.get('PUBLICATION_SCHEDULE', '')
    print(json.dumps(result, ensure_ascii=False))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as output:
            output.write('### Daily publication health\n\n```json\n')
            output.write(json.dumps(result, ensure_ascii=False, indent=2))
            output.write('\n```\n')
    if result['remaining'] < 9:
        print('::warning::Reviewed queue has fewer than 9 articles; replenish it before exhaustion.')
    if not result['ok']:
        print('::error::Daily publication check failed: ' + result['reason'])
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
