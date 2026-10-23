import importlib.util,json,re,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_build',ROOT/'scripts/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class AuditImprovementsTests(unittest.TestCase):
    def test_compact_inline_index_keeps_crawlable_cards(self):
        posts=build.load('content/posts.json')
        rendered=build.home(posts,{},__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
        inline=json.loads(re.search(r'<script id="posts-data" type="application/json">(.*?)</script>',rendered)[1])
        self.assertEqual(len(inline),len(posts))
        self.assertTrue(all('body' not in post for post in inline))
        self.assertIn('data-search-source="'+build.PREFIX+'data/posts.json?v=',rendered)
        for post in posts:self.assertIn('href="'+build.PREFIX+'post/'+post['slug']+'/"',rendered)
        self.assertIn('id="search-retry"',rendered)

    def test_local_links_escape_and_respect_base_path(self):
        for prefix in ('/','/dogu-life-preview/'):
            with patch.object(build,'PREFIX',prefix):
                html=build.inline_prose('[<strong>다음</strong>](/post/example-post/) [나쁜 링크](javascript:alert(1))')
                self.assertIn('href="'+prefix+'post/example-post/"',html)
                self.assertIn('&lt;strong&gt;',html)
                self.assertNotIn('href="javascript:',html)

    def test_og_urls_and_existing_images(self):
        posts=build.load('content/posts.json')
        for site in ('https://example.test','https://example.test/dogu-life-preview'):
            with patch.object(build,'SITE',site):
                for post in [None,*posts]:
                    html=build.shell(post['title'] if post else '홈','',post['summary'] if post else '',post)
                    metas=dict(re.findall(r'<meta property="([^"]+)" content="([^"]*)">',html))
                    self.assertTrue(metas['og:url'].startswith(site+'/'))
                    self.assertTrue(metas['og:image'].startswith(site+'/'))
                    self.assertTrue((ROOT/'docs'/metas['og:image'][len(site)+1:]).is_file())
                    self.assertIn('rel="canonical"',html)
                    self.assertIn('feed.xml',html)

    def test_pilot_internal_link_targets_exist(self):
        posts=build.load('content/posts.json');slugs={p['slug'] for p in posts}
        for post in posts:
            for slug in re.findall(r'\]\(/post/([a-z0-9-]+)/\)',post['body']):self.assertIn(slug,slugs)
