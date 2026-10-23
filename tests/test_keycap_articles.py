"""Publication safeguards for the original v1/v2 prototype records."""
import json, unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
SLUGS=['seal-keycap-blender-v1-v2','seal-keycap-stl-size-mesh-check']
class KeycapArticles(unittest.TestCase):
 def test_published_content_scope_and_sources(self):
  posts={p['slug']:p for p in json.loads((ROOT/'content/posts.json').read_text())}
  images=json.loads((ROOT/'content/illustrations.json').read_text())
  for slug,other in zip(SLUGS,reversed(SLUGS)):
   p=posts[slug]
   self.assertEqual(datetime.fromisoformat(p['published_at']).astimezone(ZoneInfo('Asia/Seoul')).date().isoformat(),'2026-10-24')
   self.assertIn('AI 어시스턴트',p['body'])
   self.assertIn('17.711 × 17.801 × 17.591mm',p['body'])
   self.assertIn('/post/'+other+'/',p['body'])
   for forbidden in ['| 미발행','검색 설명:', '## 발행 전 확인','cults3d.com','.stl)','.zip)']:
    self.assertNotIn(forbidden,p['body'])
   self.assertEqual(images[slug]['file'],'static/illustrations/seal-keycap-v1-v2-comparison.webp')
   self.assertIn('실제 출력물 사진이 아니며',images[slug]['caption'])
   self.assertIn('검증하지 않았습니다',images[slug]['caption'])
  self.assertIn('252,038',posts[SLUGS[1]]['body'])
  self.assertIn('실물 결합이 검증된 공차가 아니라',posts[SLUGS[1]]['body'])
if __name__=='__main__':unittest.main()
