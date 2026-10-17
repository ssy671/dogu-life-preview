import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'publication_automation', ROOT / 'scripts/automation.py')
automation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(automation)


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = {
            'scripts/build.py': b'print("render pages")\n',
            'scripts/automation.py': b'# render input definition\n',
            'content/posts.json': json.dumps([
                {'slug': 'first-post', 'body': 'Original article body'}
            ]).encode(),
            'content/illustrations.json': b'{}\n',
            'content/site.json': b'{"production_url":"https://example.pages.dev"}\n',
            'docs/static/site.js': b'const sort = "latest";\n',
            'docs/static/style.css': b'body { color: green; }\n',
            'docs/static/illustrations/first-post.webp': b'original image bytes',
        }
        for name, content in self.inputs.items():
            self.write(name, content)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes)
                         else content.encode())

    def fingerprint(self):
        return automation.render_fingerprint(self.root)

    def verify_current(self):
        fingerprint = self.fingerprint()
        self.assertTrue(automation.record(
            self.root, fingerprint, verified=True))
        return fingerprint

    def plan(self, event='schedule'):
        return automation.deployment_plan(self.root, event)

    def test_verified_identical_render_skips_hourly_build(self):
        fingerprint = self.verify_current()
        self.assertEqual(self.plan(), {
            'fingerprint': fingerprint, 'build': False})

    def test_explicit_push_and_manual_runs_can_verify_unchanged_render(self):
        self.verify_current()
        for event in ('push', 'workflow_dispatch'):
            with self.subTest(event=event):
                self.assertTrue(self.plan(event)['build'])

    def test_hourly_snapshots_release_state_and_generated_files_do_not_rebuild(self):
        fingerprint = self.verify_current()
        ignored = {
            'content/views.json': '{"updated_at":"2026-10-17T01:00:00Z",'
                                  '"counts":{"first-post":123}}',
            'content/state.json': '{"last_release_date":"2026-10-17"}',
            'content/queue.json': '[{"slug":"next-reviewed-post"}]',
            'docs/index.html': '<html>A generated home page</html>',
            'docs/post/first-post/index.html': '<html>A generated article</html>',
            'docs/data/views.json': '{"counts":{"first-post":123}}',
            'docs/data/build.json': '{"fingerprint":"generated-manifest"}',
            'docs/static/diagrams/first-post.svg': '<svg>Generated diagram</svg>',
            'docs/static/diagrams/nested/another.svg': '<svg>Another diagram</svg>',
        }
        for name, content in ignored.items():
            with self.subTest(path=name):
                self.write(name, content)
                self.assertEqual(self.fingerprint(), fingerprint)
                self.assertFalse(self.plan()['build'])
        # Updating the successful checkpoint itself must not change its inputs.
        marker = automation.state(self.root)
        marker['updated_at'] = '2026-10-17T02:00:00Z'
        self.write('content/deployment.json', json.dumps(marker))
        self.assertEqual(self.fingerprint(), fingerprint)
        self.assertFalse(self.plan()['build'])

    def test_new_articles_body_edits_scripts_and_assets_require_deployment(self):
        changes = {
            'new article': ('content/posts.json', json.dumps([
                {'slug': 'first-post', 'body': 'Original article body'},
                {'slug': 'second-post', 'body': 'A newly released article'}
            ]).encode()),
            'article body': ('content/posts.json', json.dumps([
                {'slug': 'first-post', 'body': 'Corrected article body'}
            ]).encode()),
            'browser behavior': ('docs/static/site.js', b'const sort = "popular";\n'),
            'stylesheet': ('docs/static/style.css', b'body { color: blue; }\n'),
            'image contents': ('docs/static/illustrations/first-post.webp', b'new image bytes'),
            'illustration mapping': ('content/illustrations.json', b'{"first-post":{"file":"new.webp"}}'),
            'site configuration': ('content/site.json', b'{"production_url":"https://new.example"}'),
            'renderer': ('scripts/build.py', b'print("render corrected pages")\n'),
            'input definition': ('scripts/automation.py', b'# revised render inputs\n'),
        }
        original = self.verify_current()
        for description, (name, content) in changes.items():
            with self.subTest(change=description):
                self.write(name, content)
                self.assertNotEqual(self.fingerprint(), original)
                self.assertTrue(self.plan()['build'])
                self.write(name, self.inputs[name])
                self.assertFalse(self.plan()['build'])

    def test_asset_addition_removal_and_rename_change_fingerprint(self):
        original = self.verify_current()
        name = 'docs/static/illustrations/first-post.webp'
        original_path = self.root / name
        added = self.root / 'docs/static/illustrations/extra.webp'
        added.write_bytes(original_path.read_bytes())
        self.assertNotEqual(self.fingerprint(), original)
        self.assertTrue(self.plan()['build'])
        added.unlink()
        self.assertEqual(self.fingerprint(), original)
        original_path.rename(added)
        self.assertNotEqual(self.fingerprint(), original)
        self.assertTrue(self.plan()['build'])
        added.unlink()
        self.assertNotEqual(self.fingerprint(), original)
        self.assertTrue(self.plan()['build'])

    def test_failed_pending_deployment_retries_even_after_source_revert(self):
        original = self.verify_current()
        name = 'docs/static/site.js'
        self.write(name, b'const brokenCandidate = true;\n')
        candidate = self.fingerprint()
        self.assertTrue(automation.record(self.root, candidate))
        pending = automation.state(self.root)
        self.assertEqual(pending['status'], 'pending')
        self.assertIsNone(pending['fingerprint'])
        self.assertEqual(pending['pending_fingerprint'], candidate)
        # A deploy or live-check failure never records a successful checkpoint.
        for _ in range(2):
            self.assertTrue(self.plan()['build'])
        self.write(name, self.inputs[name])
        self.assertEqual(self.fingerprint(), original)
        self.assertTrue(self.plan()['build'])
        self.verify_current()
        self.assertFalse(self.plan()['build'])

    def test_reverting_from_verified_b_to_previous_a_requires_deployment(self):
        original = self.verify_current()
        name = 'docs/static/site.js'
        self.write(name, b'const successfullyDeployedB = true;\n')
        deployed_b = self.verify_current()
        self.assertNotEqual(deployed_b, original)
        self.assertFalse(self.plan()['build'])
        self.write(name, self.inputs[name])
        self.assertEqual(self.fingerprint(), original)
        self.assertTrue(self.plan()['build'])

    def test_stale_checkpoint_cannot_verify_different_current_source(self):
        old_fingerprint = self.verify_current()
        self.write('content/posts.json', b'[{"slug":"newer-source"}]')
        newer_fingerprint = self.fingerprint()
        self.assertTrue(automation.record(self.root, newer_fingerprint))
        marker = self.root / 'content/deployment.json'
        before = marker.read_bytes()
        self.assertFalse(automation.record(
            self.root, old_fingerprint, verified=True))
        self.assertEqual(marker.read_bytes(), before)
        self.assertTrue(self.plan()['build'])

    def test_missing_or_invalid_checkpoint_requires_deployment(self):
        self.assertTrue(self.plan()['build'])
        for contents in ('not JSON', '[]', 'null', '{}',
                         '{"status":"verified","fingerprint":"stale"}'):
            with self.subTest(marker=contents):
                self.write('content/deployment.json', contents)
                self.assertTrue(self.plan()['build'])

    def test_fingerprint_is_independent_of_root_and_file_creation_order(self):
        with tempfile.TemporaryDirectory() as directory:
            other = Path(directory)
            for name, content in reversed(tuple(self.inputs.items())):
                path = other / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            self.assertEqual(automation.render_fingerprint(other), self.fingerprint())
        self.assertRegex(self.fingerprint(), r'^[0-9a-f]{64}$')

    def test_snapshot_and_derived_commits_skip_ci(self):
        for event, build in (('schedule', False), ('push', False), ('push', True)):
            with self.subTest(event=event, build=build):
                message = automation.commit_message(
                    published=0, build=build, event=event)
                self.assertTrue(message.startswith('[skip ci] '))

    def test_new_article_and_scheduled_recovery_commits_trigger_cloudflare(self):
        for event, published in (('schedule', 0), ('workflow_dispatch', 0),
                                 ('schedule', 3), ('push', 3),
                                 ('workflow_dispatch', 3)):
            with self.subTest(event=event, published=published):
                message = automation.commit_message(
                    published=published, build=True, event=event)
                self.assertTrue(message)
                self.assertNotIn('[skip ci]', message.lower())


if __name__ == '__main__':
    unittest.main()
