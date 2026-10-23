"""Ensure withdrawn publications and assets stay out of the current site."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SLUGS=['seal-keycap-blender-v1-v2','seal-keycap-stl-size-mesh-check']
class WithdrawnArticles(unittest.TestCase):
 def test_sources_and_generated_files_are_absent(self):
  posts=json.loads((ROOT/'content/posts.json').read_text())
  images=json.loads((ROOT/'content/illustrations.json').read_text())
  for slug in SLUGS:
   self.assertNotIn(slug,{p['slug'] for p in posts})
   self.assertNotIn(slug,images)
   self.assertFalse((ROOT/'docs/post'/slug/'index.html').exists())
   self.assertFalse((ROOT/'docs/static/diagrams'/(slug+'.svg')).exists())
  self.assertFalse((ROOT/'docs/static/illustrations/seal-keycap-v1-v2-comparison.webp').exists())
  self.assertTrue((ROOT/'docs/404.html').exists())
 def test_build_excludes_discovery(self):
  import sys
  from datetime import datetime,timezone
  sys.path.insert(0,str(ROOT/'scripts'))
  import build
  posts=json.loads((ROOT/'content/posts.json').read_text())
  rendered=build.home(posts,{},datetime.now(timezone.utc))+build.rss(posts)
  for slug in SLUGS:self.assertNotIn(slug,rendered)
  self.assertIn('if slug in published_slugs',(ROOT/'scripts/build.py').read_text())
if __name__=='__main__':unittest.main()
