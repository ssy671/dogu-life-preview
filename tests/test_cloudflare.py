import importlib.util,os,re,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]

class CloudflareBuildTests(unittest.TestCase):
 def load(self,values):
  with patch.dict(os.environ,values,clear=True):
   spec=importlib.util.spec_from_file_location('cloudflare_build',ROOT/'scripts/build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_github_default_does_not_change(self):
  m=self.load({});self.assertEqual(m.PREFIX,'/dogu-life-preview/');self.assertEqual(m.SITE,'https://ssy671.github.io/dogu-life-preview');self.assertEqual(m.VIEWS_SOURCE,'')
 def test_cloudflare_uses_root_and_external_snapshot(self):
  m=self.load({'CF_PAGES':'1','CF_PAGES_URL':'https://review.example.pages.dev'})
  self.assertEqual(m.PREFIX,'/');self.assertEqual(m.SITE,'https://lifehint-daily.pages.dev');self.assertTrue(m.VIEWS_SOURCE.endswith('/content/views.json'))
 def test_production_site_can_be_configured(self):
  m=self.load({'CF_PAGES':'1','CF_PAGES_URL':'https://preview.example.pages.dev','BLOG_SITE_URL':'https://example.pages.dev/','BLOG_BASE_PATH':'/'})
  self.assertEqual(m.SITE,'https://example.pages.dev');self.assertEqual(m.PREFIX,'/')
 def test_workers_build_uses_root_without_guessing_its_hostname(self):
  m=self.load({'WORKERS_CI':'1'})
  self.assertEqual(m.PREFIX,'/');self.assertEqual(m.SITE,'')
  self.assertTrue(m.VIEWS_SOURCE.endswith('/content/views.json'))
  post={'slug':'example','title':'Example','summary':'Summary','published_at':'2026-10-15T09:00:00+09:00'}
  self.assertNotIn('rel="canonical"',m.shell('Example','<p>Example</p>',article=post))
 def test_workers_final_hostname_can_be_configured(self):
  m=self.load({'WORKERS_CI':'1','BLOG_SITE_URL':'https://lifehint.example.workers.dev/'})
  self.assertEqual(m.SITE,'https://lifehint.example.workers.dev');self.assertEqual(m.PREFIX,'/')
 def test_all_cloudflare_page_links_and_diagrams_exist(self):
  m=self.load({'CF_PAGES':'1','CF_PAGES_URL':'https://example.pages.dev'})
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);shutil.copytree(ROOT/'content',root/'content');shutil.copytree(ROOT/'docs',root/'docs');m.ROOT=root
   count=m.build();self.assertGreaterEqual(count,18)
   class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
     for k,v in attrs:
      if k not in ['href','src'] or not v or not v.startswith('/') or v.startswith('//'):continue
      path=v[1:].split('?')[0].split('#')[0];target=root/'docs'/path
      assert target.is_file() or (target/'index.html').is_file(),v
   for p in (root/'docs').rglob('*.html'):Links().feed(p.read_text())
   home=(root/'docs/index.html').read_text();self.assertIn('data-views-source="https://raw.githubusercontent.com/',home)
   self.assertNotIn('href="/dogu-life-preview/',home)

if __name__=='__main__':unittest.main()
