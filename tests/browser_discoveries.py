"""Local Chromium checks; all external requests are blocked."""
import atexit
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/dogu-life-preview/'):
            self.path='/'+self.path[len('/dogu-life-preview/'):]
        super().do_GET()
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
atexit.register(server.server_close)
base=f'http://127.0.0.1:{server.server_port}/dogu-life-preview/'
artifacts=ROOT/'artifacts';artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width,height in [(1440,1000),(900,900),(390,900)]:
        for mode in ['light','dark']:
            context=browser.new_context(viewport={'width':width,'height':height},color_scheme=mode,is_mobile=width==390,has_touch=width==390)
            context.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base.split('/dogu-life-preview/')[0]) else route.abort())
            page=context.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'?test=1')
            expect(page.locator('#article-list article')).to_have_count(len(json.loads((ROOT/'content/posts.json').read_text())))
            expect(page.locator('.discovery-teaser')).to_be_visible()
            page.locator('header nav a',has_text='귀여운 발견').click()
            expect(page.locator('h1')).to_have_text('귀여운 발견 ✳')
            expect(page.locator('[aria-current="page"]')).to_have_text('귀여운 발견')
            expect(page.locator('.discovery-category')).to_have_count(3)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width,mode)
            assert page.locator('a[href^="https:"]').count()==0
            page.screenshot(path=str(artifacts/f'discoveries-{width}-{mode}.png'),full_page=True)
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
    context.route('https://**/*',lambda route:route.abort())
    page=context.new_page();page.goto(base+'discoveries/')
    # Natural keyboard order reaches the navigation without a mouse.
    page.keyboard.press('Tab');expect(page.locator('.brand')).to_be_focused()
    page.keyboard.press('Tab');expect(page.locator('header nav a').nth(0)).to_be_focused()
    page.keyboard.press('Tab');expect(page.locator('header nav a').nth(1)).to_be_focused()
    assert page.locator('header nav a').nth(1).evaluate('(el)=>getComputedStyle(el).outlineStyle') != 'none'
    page.keyboard.press('Enter');expect(page.locator('h1')).to_be_visible()
    assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
    browser.close()
print('PASS: discoveries 1440/900/390, light/dark, home/tab/back/search, overflow, keyboard focus and reduced motion; six screenshots saved.')
