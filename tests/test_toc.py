"""Automatic article navigation remains deterministic, escaped and image-safe."""
import importlib.util
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('toc_build', ROOT / 'scripts/build.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class TableOfContentsTests(unittest.TestCase):
    def post(self, body):
        return dict(slug='test-post', title='글 제목', category='도구 활용',
                    summary='요약', published_at='2024-01-01T09:00:00+09:00',
                    sequence=1, diagram_labels=['하나', '둘', '셋'], body=body)

    def test_korean_ids_stable_when_unrelated_section_inserted(self):
        original = module.section_ids(['## 첫 번째', '설명', '## 다음 단계'])
        updated = module.section_ids(['## 새로운 시작', '## 첫 번째', '설명 수정', '## 다음 단계'])
        self.assertEqual(original[0], updated[1])
        self.assertEqual(original[2], updated[3])
        self.assertEqual(original[0], 'section-첫-번째')

    def test_duplicate_empty_and_colliding_heading_ids_are_unique(self):
        chunks = ['## ' + title for title in ['Repeat', 'Repeat', 'Repeat-2', '!!!', '???', 'repeat']]
        ids = module.section_ids(chunks)
        self.assertEqual(len(set(ids.values())), len(chunks))
        self.assertEqual(ids, module.section_ids(chunks))
        for anchor in ids.values():
            self.assertTrue(anchor.startswith('section-'))
            self.assertNotIn(' ', anchor)

    def test_toc_and_heading_links_target_each_real_heading(self):
        post = self.post('소개\n\n## 첫 번째\n설명\n\n## 첫 번째\n둘째 설명\n\n## 마지막\n끝')
        rendered = module.article(post, [post], {})
        tags = Tags(rendered).tags
        ids = [attrs['id'] for tag, attrs in tags if tag == 'h2' and 'id' in attrs]
        fragments = [attrs['href'][1:] for tag, attrs in tags if tag == 'a' and attrs.get('href', '').startswith('#')]
        self.assertEqual(len(ids), 3)
        self.assertEqual(fragments, ids + ids)
        self.assertEqual(rendered.count('aria-label="이 글의 목차"'), 1)
        self.assertIn('<p>둘째 설명</p>', rendered)
        prose = rendered.split('<div class="prose">', 1)[1].split('</div>', 1)[0]
        self.assertEqual(prose.count('static/diagrams/test-post.svg'), 1)

    def test_heading_html_is_escaped_in_toc_heading_and_labels(self):
        post = self.post('## <script>alert("x")</script> & 제목\n안전한 본문')
        rendered = module.article(post, [post], {})
        self.assertNotIn('<script>alert(', rendered)
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; 제목', rendered)
        self.assertFalse(any(tag == 'script' and not attrs for tag, attrs in Tags(rendered).tags))

    def test_no_headings_has_no_empty_toc(self):
        post = self.post('본문만 있는 글.\n\n두 번째 문단.')
        rendered = module.article(post, [post], {})
        self.assertNotIn('class="article-toc"', rendered)
        self.assertIn('<p>본문만 있는 글.</p>', rendered)


if __name__ == '__main__':
    unittest.main()
