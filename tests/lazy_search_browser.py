"""Controlled-browser search lifecycle checks; external analytics/ads never load."""
import json
from playwright.sync_api import expect


def check_lazy_search(browser,base,posts):
    context=browser.new_context()
    context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
    context.add_init_script('''(() => {
      const original = window.fetch.bind(window);
      window.searchRequests = [];
      const timer = window.setTimeout.bind(window);
      window.setTimeout = (callback, delay, ...args) => {
        if (delay === 15000) window.searchTimeout = callback;
        return timer(callback, delay, ...args);
      };
      window.fetch = (url, options = {}) => {
        if (!String(url).includes('/data/posts.json')) return original(url, options);
        return new Promise((resolve, reject) => {
          window.searchRequests.push({resolve: (body, status = 200) => resolve(new Response(JSON.stringify(body), {status})), reject});
          options.signal?.addEventListener('abort', () => reject(new Error('aborted')));
        });
      };
    })();''')
    page=context.new_page();page.goto(base+'?test=1')
    cards=page.locator('#article-list article.card:visible')
    expect(cards).to_have_count(len(posts))
    assert page.evaluate('searchRequests.length')==0,'No initial full-text request'
    page.select_option('#sort-select','popular')
    page.locator('#category-tabs a[data-category="디지털 정리"]').click()
    assert page.evaluate('searchRequests.length')==0,'Filter/sort need no full-text request'
    page.locator('#category-tabs a[data-category=""]').click()
    def query(value):
        page.fill('#search-input',value);page.locator('#search-input').press('Enter')
    def finish(data,status=200):
        page.evaluate('([data,status]) => searchRequests.at(-1).resolve(data,status)',[data,status])
    query('not-found-lazy-check')
    expect(page.locator('#search-status')).to_be_visible()
    expect(page.locator('#empty-state')).to_be_hidden()
    expect(page.locator('#article-list')).to_have_attribute('aria-busy','true')
    query('다른 검색어')
    assert page.evaluate('searchRequests.length')==1,'Rapid changes share a request'
    page.locator('#search-reset').click()
    finish(posts)
    expect(cards).to_have_count(len(posts))
    expect(page.locator('#search-status')).to_be_hidden()
    expect(page.locator('#search-input')).to_have_value('')
    query('not-found-lazy-check')
    expect(page.locator('#empty-state')).to_be_visible()
    assert page.evaluate('searchRequests.length')==1,'Ready index is reused'
    page.go_back();expect(page.locator('#search-input')).to_have_value('')
    expect(cards).to_have_count(len(posts))
    # A URL query loads lazily too; failed/invalid responses keep useful partial results.
    page.goto(base+'?test=1&q=메일')
    expect(page.locator('#article-list')).to_have_attribute('aria-busy','true')
    finish({},503)
    expect(page.locator('#search-retry')).to_be_visible()
    expect(page.locator('#result-count')).to_contain_text('제목·요약')
    page.locator('#search-retry').click();finish([{'slug':posts[0]['slug']}])
    expect(page.locator('#search-retry')).to_be_visible()
    page.locator('#search-retry').click()
    page.evaluate("searchRequests.at(-1).reject(new Error('offline'))")
    expect(page.locator('#search-retry')).to_be_visible()
    page.locator('#search-retry').click()
    # A completion between keystroke and debounce must not overwrite newer typing.
    page.fill('#search-input','not-found-newer-input')
    finish(posts)
    expect(page.locator('#search-input')).to_have_value('not-found-newer-input')
    expect(page.locator('#empty-state')).to_be_visible()
    expect(page.locator('#article-list')).to_have_attribute('aria-busy','false')
    assert page.evaluate('searchRequests.length')==4
    page.locator('#search-reset').click();expect(cards).to_have_count(len(posts))
    # Back/forward while pending must render the current URL, never the old query.
    page.reload();query('메일');query('not-found-history')
    page.go_back();expect(page.locator('#search-input')).to_have_value('메일')
    finish(posts);expect(page.locator('#search-input')).to_have_value('메일')
    expect(cards).not_to_have_count(0)
    page.go_forward();expect(page.locator('#empty-state')).to_be_visible()
    page.reload();query('메일')
    page.evaluate('searchTimeout()')
    expect(page.locator('#search-retry')).to_be_visible()
    expect(page.locator('#article-list')).to_have_attribute('aria-busy','false')
    page.locator('#search-retry').click();finish(posts)
    expect(page.locator('#search-status')).to_be_hidden()
    context.close()
    print('Lazy search passed: no initial request, shared pending request, reset, URL/history races, HTTP/invalid/network errors, retry and debounce preservation.')
