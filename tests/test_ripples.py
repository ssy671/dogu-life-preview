"""Deterministic ripple lifecycle and template regression checks; no browser needed."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RippleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required')
    def test_lifecycle(self):
        subprocess.run(['node', 'tests/ripples_check.js'], cwd=ROOT, check=True)

    def test_shared_template_and_safe_layers(self):
        from scripts import build
        for page in [build.shell('test', '<p>본문</p>'), build.shell('test', '<a>link</a>')]:
            self.assertEqual(page.count('static/ripples.js'), 1)
            self.assertIn('defer src=', page)
        css = (ROOT / 'docs/static/upgrade.css').read_text()
        self.assertIn('pointer-events: none', css)
        self.assertIn('prefers-reduced-motion: reduce', css)
        self.assertIn('body > main', css)
        self.assertIn('background: var(--paper)', css)
        js = (ROOT / 'docs/static/ripples.js').read_text()
        for api in ['fetch(', 'localStorage', 'sessionStorage', 'sendBeacon', 'setInterval']:
            self.assertNotIn(api, js)
