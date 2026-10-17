import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'publication_runtime_state', ROOT / 'scripts/runtime_state.py')
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.remote = self.directory / 'remote.git'
        self.root = self.directory / 'source'
        self.root.mkdir()
        self.git('init', '--bare', str(self.remote))
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Source author')
        self.git('config', 'user.email', 'source@example.invalid')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.write('README.md', 'Source code stays on main.\n')
        self.write('scripts/code.py', 'print("source code")\n')
        self.write('content/views.json', {'updated_at': '2026-10-17T00:00:00Z',
                                          'counts': {'first-post': 1}})
        self.write('content/deployment.json', {'status': 'verified',
                                               'fingerprint': 'baseline'})
        self.git('add', '.')
        self.git('commit', '-m', 'Initial source')
        self.git('push', 'origin', 'main')

    def git(self, *arguments, data=None):
        return subprocess.run(
            ['git', *arguments], cwd=self.root, input=data,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True).stdout.decode().strip()

    def remote_git(self, *arguments):
        return self.git('--git-dir', str(self.remote), *arguments)

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + '\n'
                        if isinstance(value, dict) else value)

    def read(self, name):
        return json.loads((self.root / name).read_text())

    def tip(self):
        return self.remote_git('rev-parse', runtime.BRANCH)

    def source_identity(self):
        return (self.git('rev-parse', 'HEAD'),
                self.git('symbolic-ref', 'HEAD'), self.git('write-tree'),
                self.remote_git('rev-parse', 'refs/heads/main'))

    def test_initial_save_has_only_runtime_files_and_leaves_main_and_index_unchanged(self):
        before = self.source_identity()
        self.assertTrue(runtime.save(self.root))
        self.assertEqual(self.source_identity(), before)
        paths = self.remote_git('ls-tree', '-r', '--name-only', runtime.BRANCH)
        self.assertEqual(paths.splitlines(), [
            'content/deployment.json', 'content/views.json'])
        self.assertEqual(self.remote_git('show', '-s', '--format=%s', runtime.BRANCH),
                         '[skip ci] Refresh publication runtime state')
        self.assertEqual(self.remote_git('show', '-s', '--format=%an <%ae>', runtime.BRANCH),
                         f'{runtime.BOT_NAME} <{runtime.BOT_EMAIL}>')
        self.assertEqual(self.git('rev-parse', runtime.TRACKING), self.tip())
        self.assertEqual(self.remote_git('show', '-s', '--format=%P', runtime.BRANCH), '')

    def test_save_supplies_identity_when_checkout_has_no_user_configuration(self):
        self.git('config', '--unset', 'user.name')
        self.git('config', '--unset', 'user.email')
        self.assertTrue(runtime.save(self.root))
        self.assertEqual(self.remote_git('show', '-s', '--format=%an', runtime.BRANCH),
                         runtime.BOT_NAME)

    def test_load_overlays_runtime_files_without_touching_source_or_index(self):
        self.write('content/views.json', {'counts': {'first-post': 42}})
        self.write('content/deployment.json', {'status': 'pending', 'fingerprint': None})
        runtime.save(self.root)
        self.git('restore', 'content/views.json', 'content/deployment.json')
        before = self.source_identity()
        source = (self.root / 'scripts/code.py').read_bytes()
        self.assertTrue(runtime.load(self.root))
        self.assertEqual(self.read('content/views.json')['counts']['first-post'], 42)
        self.assertEqual(self.read('content/deployment.json')['status'], 'pending')
        self.assertEqual((self.root / 'scripts/code.py').read_bytes(), source)
        self.assertEqual(self.source_identity(), before)

    def test_identical_save_does_not_create_another_commit(self):
        self.assertTrue(runtime.save(self.root))
        first = self.tip()
        self.assertFalse(runtime.save(self.root))
        self.assertEqual(self.tip(), first)

    def test_later_snapshot_fast_forwards_current_remote_parent(self):
        runtime.save(self.root)
        first = self.tip()
        self.write('content/views.json', {'counts': {'first-post': 43}})
        self.assertTrue(runtime.save(self.root))
        second = self.tip()
        self.assertNotEqual(first, second)
        self.assertEqual(self.remote_git('show', '-s', '--format=%P', second), first)
        self.assertEqual(self.git('rev-parse', runtime.TRACKING), second)

    def test_changed_remote_parent_rejects_stale_local_snapshot(self):
        runtime.save(self.root)
        first = self.tip()
        other = self.directory / 'other-checkout'
        self.git('clone', '--branch', 'main', str(self.remote), str(other))
        runtime.load(other)
        path = other / 'content/views.json'
        path.write_text(json.dumps({'counts': {'first-post': 99}}))
        self.assertTrue(runtime.save(other))
        newest = self.tip()
        self.write('content/views.json', {'counts': {'first-post': 2}})
        for _ in range(2):
            with self.assertRaises(runtime.RuntimeStateError):
                runtime.save(self.root)
            self.assertEqual(self.tip(), newest)
            self.assertEqual(self.git('rev-parse', runtime.TRACKING), first)
        runtime.load(self.root)
        self.assertEqual(self.read('content/views.json')['counts']['first-post'], 99)
        self.assertFalse(runtime.save(self.root))

    def test_missing_branch_preserves_both_main_baseline_files(self):
        before = {name: (self.root / 'content' / name).read_bytes()
                  for name in runtime.FILES}
        self.assertFalse(runtime.load(self.root))
        for name, data in before.items():
            self.assertEqual((self.root / 'content' / name).read_bytes(), data)

    def test_missing_remote_checkpoint_clears_stale_baseline_checkpoint(self):
        (self.root / 'content/deployment.json').unlink()
        self.assertTrue(runtime.save(self.root))
        self.write('content/deployment.json', {'status': 'verified',
                                               'fingerprint': 'stale-main-marker'})
        self.assertTrue(runtime.load(self.root))
        self.assertFalse((self.root / 'content/deployment.json').exists())
        self.assertEqual(self.remote_git('ls-tree', '-r', '--name-only', runtime.BRANCH),
                         'content/views.json')

    def test_invalid_local_snapshot_cannot_create_or_replace_remote_state(self):
        self.write('content/views.json', '{broken JSON')
        with self.assertRaises(runtime.RuntimeStateError):
            runtime.save(self.root)
        self.assertEqual(self.git('ls-remote', '--heads', 'origin', runtime.BRANCH), '')
        self.write('content/views.json', {'counts': {'first-post': 1}})
        runtime.save(self.root)
        before = self.tip()
        for invalid in ({'counts': {'first-post': -1}},
                        {'counts': {'first-post': True}}, {'counts': []}):
            with self.subTest(snapshot=invalid):
                self.write('content/views.json', invalid)
                with self.assertRaises(runtime.RuntimeStateError):
                    runtime.save(self.root)
                self.assertEqual(self.tip(), before)

    def test_remote_failure_aborts_load_and_save_without_changing_baseline(self):
        before = (self.root / 'content/views.json').read_bytes()
        identity = self.source_identity()
        self.git('remote', 'set-url', 'origin', str(self.directory / 'missing.git'))
        with self.assertRaises(runtime.RuntimeStateError):
            runtime.load(self.root)
        with self.assertRaises(runtime.RuntimeStateError):
            runtime.save(self.root)
        self.assertEqual((self.root / 'content/views.json').read_bytes(), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), identity[0])
        self.assertEqual(self.git('write-tree'), identity[2])

    def test_invalid_remote_json_is_rejected_before_any_local_file_is_overwritten(self):
        runtime.save(self.root)
        parent = self.tip()
        blob = self.git('hash-object', '-w', '--stdin', data=b'{broken JSON\n')
        content = self.git('mktree', data=f'100644 blob {blob}\tviews.json\n'.encode())
        tree = self.git('mktree', data=f'040000 tree {content}\tcontent\n'.encode())
        corrupt = self.git('commit-tree', tree, '-p', parent, '-m', 'Corrupt runtime JSON')
        self.git('push', 'origin', f'{corrupt}:{runtime.BRANCH}')
        before = {name: (self.root / 'content' / name).read_bytes()
                  for name in runtime.FILES}
        with self.assertRaises(runtime.RuntimeStateError):
            runtime.load(self.root)
        for name, data in before.items():
            self.assertEqual((self.root / 'content' / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
