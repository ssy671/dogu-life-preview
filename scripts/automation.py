"""Track render inputs separately from hourly view snapshots."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('scripts/build.py', 'scripts/automation.py', 'content/posts.json',
          'content/illustrations.json', 'content/site.json',
          'scripts/discoveries.py', 'content/discoveries.json')


def render_fingerprint(root=ROOT):
    root = Path(root)
    paths = [root / name for name in INPUTS]
    paths += [path for path in (root / 'docs/static').rglob('*')
              if path.is_file() and 'diagrams' not in path.relative_to(root / 'docs/static').parts]
    digest = hashlib.sha256()
    for path in sorted(paths):
        name = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(name).to_bytes(4, 'big') + name)
        digest.update(len(content).to_bytes(8, 'big') + content)
    return digest.hexdigest()


def state(root=ROOT):
    try:
        value = json.loads((Path(root) / 'content/deployment.json').read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def deployment_plan(root=ROOT, event='schedule'):
    fingerprint = render_fingerprint(root)
    previous = state(root)
    needed = (event != 'schedule' or previous.get('status') != 'verified'
              or previous.get('fingerprint') != fingerprint)
    return {'fingerprint': fingerprint, 'build': needed}


def record(root, fingerprint, *, verified=False):
    root = Path(root)
    if render_fingerprint(root) != fingerprint:
        return False
    value = {'status': 'verified' if verified else 'pending',
             'fingerprint': fingerprint if verified else None,
             'updated_at': datetime.now(timezone.utc).isoformat()}
    if not verified:
        value['pending_fingerprint'] = fingerprint
    target = root / 'content/deployment.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(target)
    return True


def commit_message(*, published, build, event):
    if published:
        return 'Publish three scheduled articles'
    if build and event != 'push':
        return 'Retry and verify the current site version'
    return '[skip ci] Refresh view snapshot and generated pages'
