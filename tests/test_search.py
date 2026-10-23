"""Run the shipped JavaScript search helpers without a browser dependency."""
import shutil
import subprocess
import unittest
from pathlib import Path


class SearchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for JavaScript search checks')
    def test_search_helpers(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['node', str(root / 'tests/search_check.js')], cwd=root, check=True)
