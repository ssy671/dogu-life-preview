import importlib.util,json,tempfile,unittest
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publish',ROOT/'scripts/publish.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PublishTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'content').mkdir()
  self.posts=[{'slug':'old','published_at':'2026-10-15T00:00:00+00:00','sequence':1}]
  self.queue=[{'slug':f'new-{i}','title':f'Article {i}'} for i in range(9)]
  self.write('posts.json',self.posts);self.write('queue.json',self.queue);self.write('state.json',{'last_release_date':'2026-10-15','publish_hour':9,'daily_limit':3})
 def tearDown(self):self.tmp.cleanup()
 def write(self,n,d):(self.root/'content'/n).write_text(json.dumps(d))
 def read(self,n):return json.loads((self.root/'content'/n).read_text())
 def run_at(self,s):return module.release(self.root,datetime.fromisoformat(s))
 def test_wait_until_nine_korea(self):
  self.assertEqual(self.run_at('2026-10-15T23:59:59+00:00')['published'],0)
  self.assertEqual(len(self.read('posts.json')),1)
 def test_nine_releases_exactly_three(self):
  self.assertEqual(self.run_at('2026-10-16T00:00:00+00:00')['published'],3)
  self.assertEqual(len(self.read('posts.json')),4);self.assertEqual(len(self.read('queue.json')),6)
  self.assertEqual([p['sequence'] for p in self.read('posts.json')],[1,2,3,4])
 def test_repeat_same_day_is_idempotent(self):
  self.run_at('2026-10-16T09:00:00+09:00');self.assertEqual(self.run_at('2026-10-16T23:30:00+09:00')['published'],0)
 def test_next_day_three_more(self):
  self.run_at('2026-10-16T09:00:00+09:00');self.assertEqual(self.run_at('2026-10-17T09:00:00+09:00')['published'],3)
 def test_missing_days_do_not_bulk_publish_or_backdate(self):
  self.run_at('2026-10-20T11:05:00+09:00');posts=self.read('posts.json')
  self.assertEqual(len(posts),4);self.assertTrue(all(p['published_at'].startswith('2026-10-20') for p in posts[1:]))
 def test_short_queue_does_not_partially_release(self):
  self.write('queue.json',self.queue[:2]);self.assertEqual(self.run_at('2026-10-16T09:00:00+09:00')['published'],0)
  self.assertEqual(self.read('state.json')['last_release_date'],'2026-10-15')
 def test_stale_state_cannot_duplicate_a_completed_release(self):
  self.run_at('2026-10-16T09:00:00+09:00');self.write('state.json',{'last_release_date':'2026-10-15','publish_hour':9,'daily_limit':3})
  self.assertEqual(self.run_at('2026-10-16T10:00:00+09:00')['published'],0)

if __name__=='__main__':unittest.main()
