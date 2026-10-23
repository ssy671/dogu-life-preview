"""Exercise real sorting/filtering in a browser on the CI runner, never count test visits."""
import atexit,json,os,re,threading,urllib.request
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright,expect
from lazy_search_browser import check_lazy_search
ROOT=Path(__file__).resolve().parents[1]
check_url=os.getenv('BLOG_CHECK_URL','').strip()
if check_url:
 base=check_url.rstrip('/')+'/'
 PREFIX=urlsplit(base).path
 def fetch(path):
  request=urllib.request.Request(base+path,headers={'Cache-Control':'no-cache','User-Agent':'Dogu-Life-Browser-Check/3.0'})
  with urllib.request.urlopen(request,timeout=30) as response:
   return response.read().decode('utf-8')
 posts=json.loads(fetch('data/posts.json'))
 home=fetch('?test=1')
else:
 PREFIX='/dogu-life-preview/'
 class Handler(SimpleHTTPRequestHandler):
  def do_GET(self):
   if self.path.startswith(PREFIX):self.path='/'+self.path[len(PREFIX):]
   return super().do_GET()
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'docs')))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 def close_server():server.shutdown();server.server_close()
 atexit.register(close_server)
 base=f'http://127.0.0.1:{server.server_port}{PREFIX}'
 posts=json.loads((ROOT/'docs/data/posts.json').read_text())
 home=(ROOT/'docs/index.html').read_text()
manifest=ROOT/'content/illustrations.json'
illustrations=json.loads(manifest.read_text()) if manifest.exists() else {}
illustrated_post=next((post for post in posts if post['slug'] in illustrations),None)
article_post=illustrated_post or posts[0]
fixture={'updated_at':'2026-10-15T00:00:00Z','counts':{posts[0]['slug']:300,posts[1]['slug']:100}}
home=re.sub(r'(<script id="view-data" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(fixture)+m[2],home)
home=re.sub(r'\sdata-views-source="[^"]*"',' data-views-source=""',home)
def check_article(page,label):
 toc=page.locator('.article-toc a')
 expect(toc).not_to_have_count(0)
 fragment=toc.first.get_attribute('href')
 toc.first.click()
 assert page.evaluate("decodeURIComponent(location.hash.slice(1))") == fragment[1:]
 target=page.locator('.prose h2').first
 expect(target).to_have_attribute('id',fragment[1:])
 expect(target.locator('.section-link')).to_have_attribute('href',fragment)
 page.reload()
 expect(page.locator('.prose h2:target')).to_have_count(1)
 picture=page.locator('.post-figure img').last;picture.scroll_into_view_if_needed()
 page.wait_for_function("Array.from(document.querySelectorAll('.post-figure img')).every(i=>i.complete&&i.naturalWidth>0)")
 if illustrated_post:
  details=illustrations[illustrated_post['slug']]
  figure=page.locator('.prose > figure.article-illustration')
  expect(figure).to_have_count(1)
  image=figure.locator('img')
  expect(image).to_have_attribute('src',PREFIX+details['file'])
  expect(image).to_have_attribute('alt',details['alt'])
  expect(figure.locator('figcaption')).to_have_text(details['caption'])
  assert figure.evaluate("""figure => {
   const siblings=Array.from(figure.parentElement.children);
   const index=siblings.indexOf(figure);
   return figure.previousElementSibling?.tagName==='P' &&
    siblings.slice(index+1).some(node=>node.tagName==='P');
  }"""),'Illustration must be placed inside prose with paragraphs before and after it'
  image.scroll_into_view_if_needed()
  dimensions=image.evaluate('(img)=>img.decode().then(()=>({width:img.naturalWidth,height:img.naturalHeight}))')
  assert dimensions['width']>0 and dimensions['height']>0,'Generated raster illustration must decode'
  assert image.bounding_box()['width']<=page.viewport_size['width'],'Article image exceeds viewport'
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),'Article horizontal overflow at '+label
 assert page.locator('[data-counter-src]').get_attribute('src') is None,'Test visits must not increment counters'
 Path('artifacts').mkdir(exist_ok=True)
 page.screenshot(path='artifacts/article-'+label+'.png',full_page=True)
with sync_playwright() as p:
  browser=p.chromium.launch()
  context=browser.new_context(viewport={'width':1440,'height':1000},timezone_id='Asia/Seoul')
  context.route('https://hits.sh/**',lambda route:route.abort())
  context.route('https://pagead2.googlesyndication.com/**',lambda route:route.abort())
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
  page.goto(base+'post/'+article_post['slug']+'/?test=1');check_article(page,'desktop')
  page.set_viewport_size({'width':390,'height':844});check_article(page,'mobile')
  page.goto(base+'?test=1');page.wait_for_function("document.querySelector('#result-count').textContent.includes('개의')")
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),'Mobile horizontal overflow'
  Path('artifacts').mkdir(exist_ok=True);page.screenshot(path='artifacts/mobile.png',full_page=True)
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path='artifacts/desktop.png',full_page=True)
  snapshot_source='https://counts.example.test/views.json'
  remote_home=re.sub(r'<body[^>]*>', '<body data-views-source="'+snapshot_source+'">',home,count=1)
  remote_url=base+'?test=1&sort=popular&remote=1'
  context.route(remote_url,lambda route:route.fulfill(status=200,body=remote_home,content_type='text/html'))
  context.route(snapshot_source,lambda route:route.fulfill(status=200,body=json.dumps({'updated_at':'2026-10-15T23:59:59Z','counts':{posts[-1]['slug']:777}}),headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'}))
  page.goto(remote_url)
  expect(page.locator('#article-list article.card:visible').first).to_have_attribute('data-slug',posts[-1]['slug'])
  expect(page.locator('#article-list article.card:visible').first.locator('.view-count')).to_have_text('조회 777')
  article_path='post/'+article_post['slug']+'/'
  article_html=fetch(article_path+'?test=1') if check_url else (ROOT/'docs'/article_path/'index.html').read_text()
  article_source='https://counts.example.test/article-views.json'
  article_html=re.sub(r'<body[^>]*>', '<body data-views-source="'+article_source+'">',article_html,count=1)
  article_html,numbers_replaced=re.subn(r'(<span\b[^>]*\bdata-view-number\b[^>]*>)[^<]*(</span>)',lambda m:m[1]+'41'+m[2],article_html,count=1)
  assert numbers_replaced==1,'Article header needs a separately addressable view count'
  article_fixture={'updated_at':'2026-10-15T00:00:00Z','counts':{article_post['slug']:41}}
  article_html=re.sub(r'<script id="view-data"[^>]*>.*?</script>','',article_html,flags=re.S)
  article_html=article_html.replace('</body>','<script id="view-data" type="application/json">'+json.dumps(article_fixture)+'</script></body>')
  article_snapshot={'payload':{'updated_at':'invalid','counts':{article_post['slug']:999}},'status':200,'abort':False}
  def serve_article_snapshot(route):
   if article_snapshot['abort']:route.abort()
   else:route.fulfill(status=article_snapshot['status'],body=json.dumps(article_snapshot['payload']),headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'})
  context.route(article_source,serve_article_snapshot)
  remote_article_url=base+article_path+'?test=1&remote=1'
  context.route(remote_article_url,lambda route:route.fulfill(status=200,body=article_html,content_type='text/html'))
  page.add_init_script("""(() => {
   const setInterval = window.setInterval.bind(window);
   window.__viewRefreshCallbacks = [];
   window.setInterval = (callback, delay, ...args) => {
    if (delay === 60 * 60 * 1000) window.__viewRefreshCallbacks.push(callback);
    return setInterval(callback, delay, ...args);
   };
  })();""")
  page.goto(remote_article_url);page.wait_for_load_state('networkidle')
  article_number=page.locator('[data-view-number][data-view-slug="'+article_post['slug']+'"]')
  expect(article_number).to_have_text('41')
  assert page.locator('#article-list').count()==0,'Remote count test must exercise an article page'
  assert page.evaluate('window.__viewRefreshCallbacks.length')==1,'Article pages must schedule hourly view refreshes'
  article_snapshot['payload']={'updated_at':'2026-10-15T23:59:59Z','counts':{article_post['slug']:1234}}
  page.evaluate('() => window.__viewRefreshCallbacks[0]()')
  expect(article_number).to_have_text('1,234')
  expect(page.locator('.reading-meta .view-count small')).to_have_text('(매시간 반영)')
  for payload,status,abort in [
   ({'updated_at':'2026-10-14T23:59:59Z','counts':{article_post['slug']:999}},200,False),
   ({'updated_at':'2026-10-16T00:00:00Z','counts':{article_post['slug']:-1}},200,False),
   ({'updated_at':'2026-02-30T00:00:00Z','counts':{article_post['slug']:999}},200,False),
   ({'updated_at':'2026-10-16T00:00:00Z','counts':{}},200,False),
   ({'updated_at':'2026-10-17T00:00:00Z','counts':{article_post['slug']:999}},503,False),
   ({'updated_at':'2026-10-17T00:00:00Z','counts':{article_post['slug']:999}},200,True),
  ]:
   article_snapshot.update(payload=payload,status=status,abort=abort)
   page.evaluate('() => window.__viewRefreshCallbacks[0]()')
   expect(article_number).to_have_text('1,234')
  assert page.locator('[data-counter-src]').get_attribute('src') is None,'Remote count refreshes must not increment counters'
  # Exercise a phrase absent from metadata: this must be found in the body.
  body_query=None
  for post in posts:
   for paragraph in post.get('body','').split('\n'):
    phrase=paragraph.strip()[:18]
    if len(phrase)>8 and not phrase.startswith('#') and phrase not in (post['title']+post['summary']+post['category']):
     body_query=(post,phrase);break
   if body_query:break
  assert body_query,'Need a full-body search fixture'
  post,phrase=body_query
  page.goto(base+'?test=1')
  page.locator('#search-input').fill(phrase)
  page.locator('#search-form').evaluate('(form)=>form.requestSubmit()')
  result=page.locator('#article-list article[data-slug="'+post['slug']+'"]')
  expect(result).to_be_visible()
  expect(result.locator('.search-context mark').first).to_have_text(phrase)
  page.locator('#search-input').fill('this-query-has-no-results-123456')
  page.locator('#search-form').evaluate('(form)=>form.requestSubmit()')
  expect(page.locator('#empty-state')).to_be_visible()
  page.locator('#search-input').fill('')
  page.locator('#search-form').evaluate('(form)=>form.requestSubmit()')
  expect(page.locator('#article-list article.card:visible')).to_have_count(len(posts))
  expect(page.locator('#article-list mark')).to_have_count(0)
  print('PASS: full-body-only search, highlighted context, empty results, and clearing search.')
  from browser_ripples import check_ripples
  check_ripples(page,base)
  check_lazy_search(browser,base,posts)
  browser.close()
print(f'PASS: {base} assets, latest/popular sorting, combined filters, KST today, history, inline generated images decoded on desktop/mobile, article layout, homepage/article remote view snapshots and article snapshot failure recovery.')
