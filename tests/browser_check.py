"""Exercise real sorting/filtering in a browser on the CI runner, never count test visits."""
import json,re,threading
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
PREFIX='/dogu-life-preview/'
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  if self.path.startswith(PREFIX):self.path='/'+self.path[len(PREFIX):]
  return super().do_GET()
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}{PREFIX}'
posts=json.loads((ROOT/'docs/data/posts.json').read_text())
fixture={'updated_at':'2026-10-15T00:00:00Z','counts':{posts[0]['slug']:300,posts[1]['slug']:100}}
home=(ROOT/'docs/index.html').read_text()
home=re.sub(r'(<script id="view-data" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(fixture)+m[2],home)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  context=browser.new_context(viewport={'width':1440,'height':1000},timezone_id='Asia/Seoul')
  context.route('https://hits.sh/**',lambda route:route.abort())
  context.route('https://fonts.googleapis.com/**',lambda route:route.abort())
  context.route(base+'?test=1',lambda route:route.fulfill(status=200,body=home,content_type='text/html'))
  page=context.new_page();page.goto(base+'?test=1');page.wait_for_function("document.querySelector('#result-count').textContent.includes('개의')")
  cards=page.locator('#article-list article.card:visible');expect(cards).to_have_count(len(posts))
  latest=sorted(posts,key=lambda x:(datetime.fromisoformat(x['published_at']).timestamp(),x['sequence']),reverse=True)
  assert cards.first.get_attribute('data-slug')==latest[0]['slug'],'Latest order'
  page.select_option('#sort-select','popular');assert cards.first.get_attribute('data-slug')==posts[0]['slug'],'Popular order'
  assert 'sort=popular' in page.url
  page.select_option('#sort-select','latest');assert cards.first.get_attribute('data-slug')==latest[0]['slug']
  page.locator('#category-tabs a[data-category="디지털 정리"]').click()
  expect(cards).to_have_count(sum(p['category']=='디지털 정리' for p in posts))
  search_title=next(p['title'] for p in posts if p['slug']=='organize-downloads-folder')
  page.fill('#search-input',search_title);page.locator('#search-form button').click();expect(cards).to_have_count(1)
  assert cards.first.get_attribute('data-slug')=='organize-downloads-folder'
  page.fill('#search-input','no-match-987654');page.locator('#search-form button').click();expect(cards).to_have_count(0);expect(page.locator('#empty-state')).to_be_visible()
  page.fill('#search-input','');page.locator('#search-form button').click();page.locator('#category-tabs a[data-category=""]').click()
  page.check('#today-filter');today=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
  expect(cards).to_have_count(sum(x['date']==today for x in posts));assert 'day=today' in page.url
  page.uncheck('#today-filter');expect(cards).to_have_count(len(posts))
  page.go_back();expect(page.locator('#today-filter')).to_be_checked()
  page.goto(base+'post/'+posts[0]['slug']+'/?test=1');picture=page.locator('.post-figure img').last;picture.scroll_into_view_if_needed()
  page.wait_for_function("Array.from(document.querySelectorAll('.post-figure img')).every(i=>i.complete&&i.naturalWidth>0)")
  assert page.locator('[data-counter-src]').get_attribute('src') is None,'Test visits must not increment counters'
  page.set_viewport_size({'width':390,'height':844});page.goto(base+'?test=1');page.wait_for_function("document.querySelector('#result-count').textContent.includes('개의')")
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),'Mobile horizontal overflow'
  Path('artifacts').mkdir(exist_ok=True);page.screenshot(path='artifacts/mobile.png',full_page=True)
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path='artifacts/desktop.png',full_page=True)
  browser.close()
 print('PASS: latest/popular sorting, combined filters, KST today, history, article images and mobile layout.')
finally:server.shutdown();server.server_close()
