"""Real-browser visual/lifecycle checks, invoked by browser_check on the CI runner."""
from pathlib import Path
from playwright.sync_api import expect


def check_ripples(page, base):
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.emulate_media(reduced_motion='no-preference')
    page.goto(base + '?test=1')
    field = page.locator('body > .ripple-field')
    expect(field).to_have_attribute('aria-hidden', 'true')
    assert field.evaluate("e => getComputedStyle(e).pointerEvents") == 'none'
    page.mouse.move(12, 350)
    expect(field.locator('.water-ring')).to_have_count(1)
    # Freeze only for a deterministic screenshot of the actual rendered effect.
    page.evaluate("document.getAnimations().forEach(a => {a.pause(); a.currentTime = 350;})")
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/pointer-ripples.png')
    point = page.locator('.hero-art').evaluate('''art => {
        const r = art.getBoundingClientRect();
        for (let y = r.top + r.height * .65; y < r.bottom - 30; y += 25)
            for (let x = r.left + 55; x < r.right - 55; x += 25)
                if (document.elementFromPoint(x, y) === art) return {x, y};
    }''')
    assert point, 'Need an exposed hero background point'
    # Deliberately cross the production emission throttle between distinct gestures.
    page.wait_for_timeout(130)
    page.mouse.move(point['x'], point['y'])
    expect(page.locator('.ripple-field--art .water-ring')).to_have_count(1)
    page.evaluate("document.getAnimations().forEach(a => {a.pause(); a.currentTime = 350;})")
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    page.screenshot(path='artifacts/pointer-ripples-hero.png')
    page.emulate_media(reduced_motion='reduce')
    expect(page.locator('.water-ring')).to_have_count(0)
    page.mouse.move(20, 400)
    expect(page.locator('.water-ring')).to_have_count(0)
    page.emulate_media(reduced_motion='no-preference')
    page.locator('#search-input').hover()
    expect(page.locator('.water-ring')).to_have_count(0)
    page.mouse.move(15, 450)
    expect(field.locator('.water-ring')).to_have_count(1)
    page.set_viewport_size({'width': 1400, 'height': 950})
    expect(page.locator('.water-ring')).to_have_count(0)
    # Touch emulation must not opt into decorative motion.
    touch = page.context.browser.new_context(is_mobile=True, has_touch=True, viewport={'width':390,'height':844})
    try:
        touch.route('https://hits.sh/**', lambda route: route.abort())
        touch.route('https://pagead2.googlesyndication.com/**', lambda route: route.abort())
        mobile = touch.new_page()
        mobile.goto(base + '?test=1')
        mobile.dispatch_event('body', 'pointermove', {'pointerType':'mouse','clientX':5,'clientY':300})
        expect(mobile.locator('.water-ring')).to_have_count(0)
        assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        mobile.screenshot(path='artifacts/mobile-viewport.png')
    finally:
        touch.close()
    print('PASS: pointer ripple rendering, pointer transparency, reduced-motion change, controls, resize, and touch opt-out.')
