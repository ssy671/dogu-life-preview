"""Store view snapshots and deployment checkpoints away from the source branch."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BRANCH = 'refs/heads/publication-state'
TRACKING = 'refs/remotes/origin/publication-state'
FILES = ('views.json', 'deployment.json')
MESSAGE = '[skip ci] Refresh publication runtime state'
BOT_NAME = 'github-actions[bot]'
BOT_EMAIL = '41898282+github-actions[bot]@users.noreply.github.com'


class RuntimeStateError(RuntimeError):
    """Runtime state could not be read or saved reliably."""


def _git(root, *arguments, data=None):
    result = subprocess.run(
        ['git', *arguments], cwd=root, input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        # Avoid including remote URLs or credential-helper output in an error.
        raise RuntimeStateError(
            f'Git runtime-state operation failed: {arguments[0]} '
            f'(exit {result.returncode})')
    return result.stdout


def _remote_tip(root):
    advertised = _git(root, 'ls-remote', '--heads', 'origin', BRANCH).decode().strip()
    if not advertised:
        return None
    lines = advertised.splitlines()
    if len(lines) != 1:
        raise RuntimeStateError('Unexpected publication-state branch response')
    fields = lines[0].split()
    if (len(fields) != 2 or fields[1] != BRANCH
            or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', fields[0])):
        raise RuntimeStateError('Invalid publication-state branch response')
    # Fetch the exact branch, including its tree, before using it as a parent.
    _git(root, 'fetch', '--no-tags', '--depth=1', 'origin', f'+{BRANCH}:{TRACKING}')
    return _git(root, 'rev-parse', TRACKING).decode().strip()


def _validate(name, data):
    try:
        value = json.loads(data)
    except (UnicodeError, ValueError) as error:
        raise RuntimeStateError(f'Invalid runtime JSON: {name}') from error
    if not isinstance(value, dict):
        raise RuntimeStateError(f'Runtime JSON must be an object: {name}')
    if name == 'views.json':
        counts = value.get('counts')
        if (not isinstance(counts, dict)
                or any(type(count) is not int or count < 0
                       for count in counts.values())):
            raise RuntimeStateError('Runtime views must contain nonnegative integer counts')


def _replace(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load(root=ROOT):
    """Overlay runtime files, preserving the source baseline if no branch exists.

    A missing deployment marker invalidates any baseline checkpoint. Git/auth
    errors and malformed remote snapshots abort instead of silently using old
    counters or a stale successful checkpoint.
    """
    root = Path(root)
    tip = _remote_tip(root)
    if tip is None:
        _git(root, 'update-ref', '-d', TRACKING)
        return False
    entries = _git(root, 'ls-tree', '-r', '--name-only', tip).decode().splitlines()
    if ('content/views.json' not in entries
            or set(entries) - {f'content/{name}' for name in FILES}):
        raise RuntimeStateError('Publication-state branch must contain only runtime JSON files')
    payloads = {}
    for name in FILES:
        if f'content/{name}' in entries:
            payloads[name] = _git(root, 'show', f'{tip}:content/{name}')
            _validate(name, payloads[name])
    for name, data in payloads.items():
        _replace(root / 'content' / name, data)
    if 'deployment.json' not in payloads:
        (root / 'content/deployment.json').unlink(missing_ok=True)
    return True


def save(root=ROOT):
    """Fast-forward the dedicated branch without checking it out or staging files."""
    root = Path(root)
    payloads = {}
    for name in FILES:
        path = root / 'content' / name
        if path.exists():
            payloads[name] = path.read_bytes()
            _validate(name, payloads[name])
    if 'views.json' not in payloads:
        raise RuntimeStateError('A view snapshot is required before saving runtime state')
    loaded_parent = _git(root, 'for-each-ref', '--format=%(objectname)',
                         TRACKING).decode().strip() or None
    parent = _remote_tip(root)
    if parent != loaded_parent:
        # The local files were based on the previous load, not the newly
        # fetched snapshot. Require a fresh load rather than overwriting it.
        if loaded_parent is None:
            _git(root, 'update-ref', '-d', TRACKING)
        else:
            _git(root, 'update-ref', TRACKING, loaded_parent)
        raise RuntimeStateError('Publication runtime changed remotely; load it again before saving')
    entries = []
    for name, data in sorted(payloads.items()):
        blob = _git(root, 'hash-object', '-w', '--stdin', data=data).decode().strip()
        entries.append(f'100644 blob {blob}\t{name}\n')
    content_tree = _git(root, 'mktree', data=''.join(entries).encode()).decode().strip()
    tree = _git(root, 'mktree', data=f'040000 tree {content_tree}\tcontent\n'.encode()).decode().strip()
    if parent is not None:
        previous_tree = _git(root, 'rev-parse', f'{parent}^{{tree}}').decode().strip()
        if previous_tree == tree:
            return False
    arguments = ['-c', f'user.name={BOT_NAME}', '-c', f'user.email={BOT_EMAIL}',
                 'commit-tree', tree, '-m', MESSAGE]
    if parent is not None:
        arguments += ['-p', parent]
    commit = _git(root, *arguments).decode().strip()
    # A concurrent remote write rejects this push; never overwrite it by force.
    _git(root, 'push', 'origin', f'{commit}:{BRANCH}')
    _git(root, 'update-ref', TRACKING, commit)
    return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('load', 'save'))
    arguments = parser.parse_args()
    changed = {'load': load, 'save': save}[arguments.operation]()
    print(f'Publication runtime {arguments.operation}: {"updated" if changed else "unchanged"}.')
