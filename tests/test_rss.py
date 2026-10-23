import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rss_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class RssTests(unittest.TestCase):
    def setUp(self):
        self.posts = json.loads((ROOT / 'content/posts.json').read_text())[:2]

    def test_feed_has_published_posts_newest_first_and_escaped_text(self):
        self.posts[0]['title'] = '한글 <태그> & "제목"'
        self.posts[0]['summary'] = '본문 & <script>alert(1)</script>'
        tree = ET.fromstring(build.rss(self.posts))
        items = tree.findall('channel/item')
        expected = sorted(self.posts, key=build.order, reverse=True)
        self.assertEqual(len(items), len(expected))
        for item, post in zip(items, expected):
            self.assertEqual(item.findtext('title'), post['title'])
            self.assertEqual(item.findtext('description'), post['summary'])
            self.assertTrue(item.findtext('link').startswith('https://'))
            self.assertTrue(item.findtext('link').endswith('/post/' + post['slug'] + '/'))
            self.assertEqual(item.findtext('guid'), item.findtext('link'))
            self.assertIsNotNone(parsedate_to_datetime(item.findtext('pubDate')).tzinfo)
            self.assertEqual(item.findall('.//script'), [])

    def test_feed_handles_empty_posts_and_workers_without_site(self):
        with patch.object(build, 'SITE', ''):
            tree = ET.fromstring(build.rss(self.posts))
            self.assertEqual(tree.findtext('channel/link'), build.PRODUCTION_SITE + '/')
        self.assertEqual(ET.fromstring(build.rss([])).findall('channel/item'), [])

    def test_feed_discovery_and_subscription_respect_base_path(self):
        for prefix in ('/', '/dogu-life-preview/'):
            with patch.object(build, 'PREFIX', prefix):
                page = build.shell('제목', '<p>본문</p>')
                self.assertIn('rel="alternate" type="application/rss+xml"', page)
                self.assertEqual(page.count('href="' + prefix + 'feed.xml"'), 2)
                self.assertIn('RSS 구독', page)

    def test_public_search_data_contains_body_and_json_is_script_safe(self):
        post = self.posts[0]
        post['body'] = '</script><script>alert(1)</script>'
        data = build.public(post)
        self.assertEqual(data['body'], post['body'])
        self.assertNotIn('<', build.dump(data))
        self.assertEqual(json.loads(build.dump(data)), data)


if __name__ == '__main__':
    unittest.main()
