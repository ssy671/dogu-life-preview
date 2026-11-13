"""Discovery shelf checks against a local build or BLOG_CHECK_URL."""
import atexit
import json
import os
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/dogu-life-preview/'):
            self.path='/'+self.path[len('/dogu-life-preview/'):]
        super().do_GET()
    def log_message(self,*args): pass
base=os.environ.get('BLOG_CHECK_URL','').rstrip('/')+'/' if os.environ.get('BLOG_CHECK_URL') else ''
if not base:
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    atexit.register(server.server_close)
    base=f'http://127.0.0.1:{server.server_port}/dogu-life-preview/'
origin=urlsplit(base).netloc
items=json.loads((ROOT/'content/discoveries.json').read_text())['items']
def allow_site(route):
    route.continue_() if urlsplit(route.request.url).netloc==origin else route.abort()
artifacts=ROOT/'artifacts';artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width,height in [(1440,1000),(900,900),(390,900)]:
        for mode in ['light','dark']:
            context=browser.new_context(viewport={'width':width,'height':height},color_scheme=mode,is_mobile=width==390,has_touch=width==390)
            context.route('**/*',allow_site)
            page=context.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'?test=1')
            expect(page.locator('#article-list article')).to_have_count(len(json.loads((ROOT/'content/posts.json').read_text())))
            expect(page.locator('.discovery-teaser')).to_be_visible()
            page.locator('header nav a',has_text='귀여운 발견').click()
            expect(page.locator('h1')).to_have_text('귀여운 발견')
            expect(page.locator('[aria-current="page"]')).to_have_text('귀여운 발견')
            expect(page.locator('.discovery-category')).to_have_count(3)
            # A navigation click can finish before the new stylesheet has applied.
            page.wait_for_load_state('load')
            expect(page.locator('body')).to_have_css('overflow-wrap', 'anywhere')
            expect(page.locator('.discovery-item')).to_have_count(len(items))
            for item in items:
                card=page.locator('.discovery-item').filter(has=page.get_by_role('heading',name=item['title'],exact=True))
                expect(card).to_have_count(1)
                expect(card.locator('.discovery-badge')).to_have_text('미사용 발견' if item['experience']=='found' else '직접 사용')
                expect(card).to_contain_text(item['checked_at'])
                if item['affiliate'] is None: expect(card).to_contain_text('제휴·협찬 관계 미확인')
                if item.get('price_note'): expect(card).to_contain_text(item['price_note'])
                links={item['source_url'],item.get('seller_url',item['source_url'])}
                picture=item.get('image')
                if picture:
                    links.add(picture['source_url'])
                    photo=card.locator('.discovery-photo img')
                    expect(photo).to_have_count(1)
                    expect(photo).to_have_attribute('alt',picture['alt'])
                    photo.scroll_into_view_if_needed()
                    photo.evaluate('(img)=>img.decode()')
                    assert photo.evaluate('(img)=>img.complete && img.naturalWidth > 0')
                    expect(card.locator('figcaption')).to_contain_text(picture['credit'])
                else:
                    expect(card.locator('.discovery-photo-link')).to_be_visible()
                assert set(card.locator('a').evaluate_all('(links)=>links.map(link=>link.href)'))==links
                for rel in card.locator('a').evaluate_all('(links)=>links.map(link=>link.rel)'):
                    assert 'noopener' in rel and 'noreferrer' in rel
            expect(page.locator('.discovery-empty')).to_have_count(0 if items else 1)
            page.screenshot(path=str(artifacts/f'discoveries-{width}-{mode}.png'),full_page=True)
            overflow=page.evaluate('''() => ({viewport: innerWidth, width: document.documentElement.scrollWidth, elements: [...document.querySelectorAll('body *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map(el => ({tag: el.tagName, className: String(el.className), right: el.getBoundingClientRect().right}))})''')
            assert overflow['width'] <= overflow['viewport'], (width, mode, overflow)
            page.locator('a[href="#selection-guide"]').click()
            assert page.url.endswith('#selection-guide')
            page.locator('.discovery-return a').click()
            expect(page.locator('#article-list')).to_be_visible()
            page.go_back();expect(page.locator('#guide-title')).to_be_visible()
            page.locator('.brand').click();expect(page.locator('#search-input')).to_be_visible()
            page.locator('#search-input').fill('다운로드');page.locator('#search-form button').click()
            expect(page.locator('#article-list article:visible').first).to_be_visible()
            assert not errors, errors
            context.close()
    context=browser.new_context(viewport={'width':390,'height':900},reduced_motion='reduce')
    context.route('**/*',allow_site)
    page=context.new_page();page.goto(base+'discoveries/')
    # Natural keyboard order reaches the navigation without a mouse.
    page.keyboard.press('Tab');expect(page.locator('.brand')).to_be_focused()
    page.keyboard.press('Tab');expect(page.locator('header nav a').nth(0)).to_be_focused()
    page.keyboard.press('Tab');expect(page.locator('header nav a').nth(1)).to_be_focused()
    assert page.locator('header nav a').nth(1).evaluate('(el)=>getComputedStyle(el).outlineStyle') != 'none'
    page.keyboard.press('Enter');expect(page.locator('h1')).to_be_visible()
    assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
    browser.close()
print('PASS: discoveries 1440/900/390, light/dark, product image decoding and attribution, official-photo links, home/tab/back/search, overflow, keyboard focus and reduced motion; six screenshots saved.')
