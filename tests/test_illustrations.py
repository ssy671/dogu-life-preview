import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ArticleIllustrationTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {}, clear=True):
            spec = importlib.util.spec_from_file_location('illustration_build', ROOT / 'scripts/build.py')
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.module.ROOT = self.root
        (self.root / 'content').mkdir()
        (self.root / 'docs/static/illustrations').mkdir(parents=True)
        self.post = {
            'slug': 'organize-work-folders', 'title': '폴더 정리', 'summary': '작게 정리해 봅니다.',
            'category': '디지털 정리', 'sequence': 1, 'published_at': '2024-01-01T09:00:00+09:00',
            'diagram_labels': ['분류', '정리', '확인'],
            'body': '처음 읽는 문단.\n\n## 첫 번째\n\n첫 절의 첫 문단.\n\n첫 절의 마지막 문단.\n\n## 두 번째\n\n두 번째 절의 첫 문단.\n\n두 번째 절의 마지막 문단.\n\n## 세 번째\n\n마지막 절의 문단.',
        }
        self.details = {
            'file': 'static/illustrations/organize-work-folders.webp',
            'alt': '진행 중인 자료와 보관 자료를 나눈 서류함',
            'caption': '파일의 목적에 따라 자리를 나눕니다.',
            'after_heading': '두 번째',
        }
        (self.root / 'docs' / self.details['file']).write_bytes(b'fixture')

    def write_manifest(self, details=None, slug=None):
        (self.root / 'content/illustrations.json').write_text(json.dumps({slug or self.post['slug']: details or self.details}))

    def test_places_image_after_matching_section_and_preserves_all_prose(self):
        self.write_manifest()
        mapping = self.module.load_illustrations([self.post])
        rendered = self.module.article(self.post, [self.post], {}, mapping[self.post['slug']])
        prose = rendered.split('<div class="prose">', 1)[1].split('</div>', 1)[0]
        illustration_at = prose.index('<figure class="post-figure article-illustration">')
        self.assertLess(prose.index('<p>두 번째 절의 마지막 문단.</p>'), illustration_at)
        self.assertLess(illustration_at, prose.index(self.module.prose('## 세 번째')))
        for paragraph in self.post['body'].split('\n\n'):
            self.assertIn(self.module.prose(paragraph), prose)
        self.assertEqual(prose.count('static/diagrams/organize-work-folders.svg'), 1)
        self.assertEqual(prose.count('static/illustrations/organize-work-folders.webp'), 1)
        self.assertNotIn('static/organize-folders.webp', rendered)
        self.assertIn('width="1536" height="1024" loading="lazy" decoding="async"', prose)

    def test_fallback_inserts_between_paragraphs_away_from_original_diagram(self):
        self.details.pop('after_heading')
        self.write_manifest()
        mapped = self.module.load_illustrations([self.post])[self.post['slug']]
        rendered = self.module.article(self.post, [self.post], {}, mapped)
        prose = rendered.split('<div class="prose">', 1)[1].split('</div>', 1)[0]
        figure_at = prose.index('<figure class="post-figure article-illustration">')
        self.assertTrue(prose[:figure_at].endswith('</p>'))
        self.assertLess(prose.index('static/diagrams/'), figure_at)
        self.assertGreater(figure_at, prose.index(self.module.prose('## 두 번째')))
        self.assertLess(figure_at, prose.index('<p>마지막 절의 문단.</p>'))

    def test_single_newline_after_heading_preserves_paragraphs_and_exact_placement(self):
        self.post['body'] = (
            '처음 읽는 문단.\n이어지는 설명.\n\n'
            '## 첫 번째\n첫 절의 첫 문단.\n같은 문단의 두 번째 줄.\n\n'
            '첫 절의 마지막 문단.\n\n'
            '## 두 번째\n두 번째 절의 첫 문단.\n\n'
            '두 번째 절의 마지막 문단.\n'
            '## 세 번째\n\n마지막 절의 문단.'
        )
        self.write_manifest()
        mapped = self.module.load_illustrations([self.post])[self.post['slug']]
        rendered = self.module.article(self.post, [self.post], {}, mapped)
        prose = rendered.split('<div class="prose">', 1)[1].split('</div>', 1)[0]
        self.assertIn('<p>처음 읽는 문단.<br>이어지는 설명.</p>', prose)
        self.assertIn(self.module.prose('## 첫 번째') + '<p>첫 절의 첫 문단.<br>같은 문단의 두 번째 줄.</p>', prose)
        self.assertIn('<p>첫 절의 마지막 문단.</p>', prose)
        self.assertIn(self.module.prose('## 두 번째') + '<p>두 번째 절의 첫 문단.</p>', prose)
        self.assertIn(self.module.prose('## 세 번째') + '<p>마지막 절의 문단.</p>', prose)
        illustration_at = prose.index('<figure class="post-figure article-illustration">')
        self.assertTrue(prose[:illustration_at].endswith('<p>두 번째 절의 마지막 문단.</p>'))
        self.assertLess(illustration_at, prose.index(self.module.prose('## 세 번째')))
        self.assertEqual(prose.count('static/diagrams/organize-work-folders.svg'), 1)

    def test_unmapped_article_and_absent_manifest_keep_original_figures(self):
        self.assertEqual(self.module.load_illustrations([self.post]), {})
        rendered = self.module.article(self.post, [self.post], {})
        self.assertIn('static/organize-folders.webp', rendered)
        self.assertIn('static/diagrams/organize-work-folders.svg', rendered)
        self.assertNotIn('article-illustration', rendered)

    def test_missing_asset_stops_build_before_any_page_is_written(self):
        self.write_manifest({**self.details, 'file': 'static/illustrations/missing.webp'})
        for name, value in [('posts', [self.post]), ('views', {'counts': {}})]:
            (self.root / f'content/{name}.json').write_text(json.dumps(value))
        home = self.root / 'docs/index.html'
        home.write_text('original page')
        with self.assertRaisesRegex(ValueError, 'asset is missing.*organize-work-folders'):
            self.module.build()
        self.assertEqual(home.read_text(), 'original page')
        self.assertFalse((self.root / 'docs/post').exists())
        self.assertFalse((self.root / 'docs/static/diagrams').exists())

    def test_invalid_manifest_paths_and_heading_fail_with_article_context(self):
        for changes, message in [
            ({'file': '../outside.webp'}, 'local image path'),
            ({'file': str(self.root / 'docs' / self.details['file'])}, 'local image path'),
            ({'alt': ''}, 'nonempty alt'),
            ({'after_heading': '존재하지 않는 제목'}, 'heading not found'),
            ({'width': 1024}, 'width and height together'),
            ({'width': True, 'height': 1024}, 'positive integer'),
        ]:
            with self.subTest(changes=changes):
                self.write_manifest({**self.details, **changes})
                with self.assertRaisesRegex(ValueError, 'Illustration organize-work-folders.*' + message):
                    self.module.load_illustrations([self.post])

    def test_future_mapping_and_custom_dimensions_work_at_cloudflare_root(self):
        self.details.update(width=1024, height=1024)
        self.write_manifest(slug='future-post')
        self.assertIn('future-post', self.module.load_illustrations([self.post]))
        self.module.PREFIX = '/'
        rendered = self.module.article(self.post, [self.post], {}, self.details)
        self.assertIn('src="/static/illustrations/organize-work-folders.webp"', rendered)
        self.assertIn('width="1024" height="1024" loading="lazy"', rendered)


if __name__ == '__main__':
    unittest.main()
