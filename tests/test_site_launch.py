import importlib.util
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = 'https://lifehint-daily.pages.dev'
CLIENT = 'ca-pub-2217472724331923'


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.items = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))

    def matching(self, tag, **attrs):
        return [value for name, value in self.items
                if name == tag and all(value.get(key) == expected
                                       for key, expected in attrs.items())]


class SiteLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ('content', 'docs', 'scripts'):
            shutil.copytree(ROOT / directory, self.root / directory)
        self.docs = self.root / 'docs'

    def build(self, environment):
        with patch.dict(os.environ, environment, clear=True):
            spec = importlib.util.spec_from_file_location(
                'site_launch_build', ROOT / 'scripts/build.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.ROOT = self.root
            module.build()
        return module

    def production_environment(self):
        return {'CF_PAGES': '1', 'CF_PAGES_BRANCH': 'main',
                'CF_PAGES_URL': 'https://deployment-hash.lifehint-daily.pages.dev'}

    def assert_private_build(self):
        for file in self.docs.rglob('*.html'):
            source = file.read_text()
            tags = Tags(source)
            with self.subTest(page=file.relative_to(self.docs)):
                self.assertEqual(len(tags.matching('meta', name='robots')), 1)
                self.assertIn('noindex', tags.matching('meta', name='robots')[0]['content'])
                self.assertNotIn('pagead2.googlesyndication.com', source)
                self.assertFalse(tags.matching('meta', name='google-adsense-account'))
        self.assertIn('Disallow: /', (self.docs / 'robots.txt').read_text())
        self.assertFalse((self.docs / 'ads.txt').exists())
        self.assertFalse((self.docs / 'sitemap.xml').exists())

    def test_production_pages_share_verified_ad_account_and_stable_canonicals(self):
        module = self.build(self.production_environment())
        self.assertTrue(module.PUBLIC_SITE)
        self.assertEqual(module.SITE, PRODUCTION)
        files = list(self.docs.rglob('*.html'))
        self.assertGreater(len(files), 4)
        for file in files:
            source = file.read_text()
            tags = Tags(source)
            directory = file.relative_to(self.docs).parent.as_posix()
            path = '/' if directory == '.' else '/' + directory + '/'
            with self.subTest(page=path):
                scripts = [attrs for tag, attrs in tags.items if tag == 'script'
                           and attrs.get('src', '').startswith(
                               'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?')]
                self.assertEqual(len(scripts), 1)
                self.assertIn('client=' + CLIENT, scripts[0]['src'])
                self.assertIn('async', scripts[0])
                self.assertEqual(tags.matching('meta', name='google-adsense-account'),
                                 [{'name': 'google-adsense-account', 'content': CLIENT}])
                self.assertEqual(tags.matching('link', rel='canonical'),
                                 [{'rel': 'canonical', 'href': PRODUCTION + path}])
                robots = tags.matching('meta', name='robots')
                self.assertEqual(len(robots), 1)
                self.assertNotIn('noindex', robots[0]['content'])
                self.assertNotIn('nofollow', robots[0]['content'])
                self.assertNotIn('화면 확인용 미리보기', source)

    def test_production_crawling_files_match_the_pages_they_describe(self):
        self.build(self.production_environment())
        self.assertEqual((self.docs / 'ads.txt').read_text().strip(),
                         'google.com, pub-2217472724331923, DIRECT, f08c47fec0942fa0')
        robots = (self.docs / 'robots.txt').read_text()
        self.assertNotIn('Disallow: /', robots)
        self.assertIn('Sitemap: ' + PRODUCTION + '/sitemap.xml', robots)
        tree = ET.fromstring((self.docs / 'sitemap.xml').read_text())
        urls = [element.text for element in tree.iter()
                if element.tag.rsplit('}', 1)[-1] == 'loc']
        expected = {PRODUCTION + '/', PRODUCTION + '/about/',
                    PRODUCTION + '/contact/', PRODUCTION + '/privacy/'}
        expected.update(PRODUCTION + '/' + file.relative_to(self.docs).parent.as_posix() + '/'
                        for file in (self.docs / 'post').rglob('index.html'))
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(set(urls), expected)

    def test_preview_github_and_workers_have_no_ads_or_public_crawling_files(self):
        environments = [
            {},
            {'WORKERS_CI': '1'},
            {'WORKERS_CI': '1', 'BLOG_SITE_URL': PRODUCTION},
            {'CF_PAGES': '1', 'CF_PAGES_BRANCH': 'feature',
             'CF_PAGES_URL': 'https://preview.lifehint-daily.pages.dev'},
            {'CF_PAGES': '1', 'CF_PAGES_BRANCH': 'main',
             'BLOG_SITE_URL': 'https://other.pages.dev'},
        ]
        for environment in environments:
            with self.subTest(environment=environment):
                # A prior production build must not leak ads or crawler files.
                self.build(self.production_environment())
                module = self.build(environment)
                self.assertFalse(module.PUBLIC_SITE)
                self.assert_private_build()

    def test_public_support_pages_no_longer_describe_an_unconnected_preview(self):
        self.build(self.production_environment())
        contact = (self.docs / 'contact/index.html').read_text()
        privacy = (self.docs / 'privacy/index.html').read_text()
        self.assertNotIn('관리자 화면', contact)
        self.assertNotIn('광고와 결제 서비스는 연결되어 있지 않습니다', privacy)
        self.assertIn('Google', privacy)
        self.assertIn('쿠키', privacy)
        self.assertIn('개인 맞춤', privacy)
        self.assertTrue('adssettings.google.com' in privacy or
                        'myadcenter.google.com' in privacy or
                        'www.google.com/settings/ads' in privacy)


if __name__ == '__main__':
    unittest.main()
