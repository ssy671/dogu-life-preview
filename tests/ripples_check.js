const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('docs/static/ripples.js', 'utf8');
function setup({ reduced = false, fine = true, art = true, supported = true } = {}) {
  const animations = [];
  class Target {
    constructor() { this.events = {}; this.children = []; this.style = {}; this.attrs = {}; this.classes = new Set(); this.classList = { add: c => this.classes.add(c), toggle: (c, on) => on ? this.classes.add(c) : this.classes.delete(c) }; }
    addEventListener(type, fn) { (this.events[type] ||= new Set()).add(fn); }
    removeEventListener(type, fn) { this.events[type]?.delete(fn); }
    fire(type, event = {}) { for (const fn of [...(this.events[type] || [])]) fn(event); }
    prepend(node) { this.children.unshift(node); node.parent = this; }
    append(node) { this.children.push(node); node.parent = this; }
    remove() { this.parent.children = this.parent.children.filter(n => n !== this); }
    setAttribute(key, value) { this.attrs[key] = value; }
    cloneNode() { const n = new Target(); n.attrs = {...this.attrs}; return n; }
    getBoundingClientRect() { return { left: 100, top: 100 }; }
    animate(frames, options) {
      const a = { node: this, frames, options, cancel() { this.cancelled = true; }, finish() { this.onfinish(); } };
      animations.push(a); return a;
    }
  }
  const document = new Target(), window = new Target();
  document.body = new Target(); document.documentElement = new Target();
  const hero = art ? new Target() : null;
  document.createElement = () => new Target(); document.querySelector = () => hero;
  const motion = new Target(), pointer = new Target(); motion.matches = reduced; pointer.matches = fine;
  let time = 0, observer;
  class IntersectionObserver { constructor(callback) { observer = callback; } observe() {} }
  vm.runInNewContext(source, {document, window, Element: {prototype: supported ? {animate() {}} : {}}, matchMedia: q => q.includes('reduce') ? motion : pointer, performance: {now: () => time}, IntersectionObserver, Math, Set});
  const move = (overrides = {}, delta = 120) => { time += delta; document.fire('pointermove', {pointerType: 'mouse', buttons: 0, clientX: time, clientY: 20, target: document.body, ...overrides}); };
  return { document, window, motion, pointer, hero, move, animations, intersect: visible => observer?.([{target:hero,isIntersecting:visible}]) };
}
for (const options of [{reduced:true}, {fine:false}, {supported:false}]) {
  const h=setup(options);h.move();assert.equal(h.animations.length,0);
}
{
  const h=setup(); const field=h.document.body.children[0];
  assert.equal(field.attrs['aria-hidden'],'true');
  h.move({pointerType:'touch'});h.move({pointerType:'pen'});h.move({buttons:1});h.move({target:{tagName:'A'}});
  assert.equal(h.animations.length,0);
  h.move();assert.equal(field.children.length,1);
  h.move({},10);assert.equal(h.animations.length,1, 'throttled');
  for(let i=0;i<20;i++)h.move();assert.equal(field.children.length,8,'bounded rings');
  h.animations[0].finish();assert.equal(field.children.length,7);
  h.move();assert.equal(field.children.length,8);
  h.document.hidden=true;h.document.fire('visibilitychange');assert.equal(field.children.length,0);
  const count=h.animations.length;h.move();assert.equal(h.animations.length,count);
  h.document.hidden=false;h.document.fire('visibilitychange');h.move();assert.equal(field.children.length,1);
  h.motion.matches=true;h.motion.fire('change');assert.equal(field.children.length,0);
  h.motion.matches=false;h.motion.fire('change');h.move();assert.equal(field.children.length,1);
  h.pointer.matches=false;h.pointer.fire('change');assert.equal(field.children.length,0);
  h.pointer.matches=true;h.pointer.fire('change');
  h.move({target:h.hero,clientX:120,clientY:140});
  const ring=h.hero.children[0].children[0];assert.equal(ring.style.left,'20px');assert.equal(ring.style.top,'40px');
  h.window.fire('resize');assert.equal(h.hero.children[0].children.length,0);
  h.window.fire('pagehide');h.move();assert.equal(field.children.length,0);
  h.window.fire('pageshow');h.window.fire('pageshow');h.move();assert.equal(field.children.length,1);
  assert.equal(h.document.events.pointermove.size,1,'no duplicate listeners on bfcache restore');
}
{ const h=setup({art:false});h.move();assert.equal(h.animations.length,1); }
console.log('PASS ripple lifecycle, bounds, opt-outs, target safety, article pages and bfcache');

{
 const h=setup({fine:false});const field=h.hero.children[0];
 assert(!field.classes.has('ripple-ambient'),'off until observed visible');
 h.intersect(true);assert(field.classes.has('ripple-ambient'));
 h.move();assert.equal(h.animations.length,0,'no JS pointer animations on mobile');
 h.intersect(false);assert(!field.classes.has('ripple-ambient'));
 h.intersect(true);h.document.hidden=true;h.document.fire('visibilitychange');assert(!field.classes.has('ripple-ambient'));
 h.document.hidden=false;h.document.fire('visibilitychange');assert(field.classes.has('ripple-ambient'));
 h.motion.matches=true;h.motion.fire('change');assert(!field.classes.has('ripple-ambient'));
 h.motion.matches=false;h.motion.fire('change');assert(field.classes.has('ripple-ambient'));
 h.window.fire('pagehide');assert(!field.classes.has('ripple-ambient'));
 h.window.fire('pageshow');assert(field.classes.has('ripple-ambient'));
 h.pointer.matches=true;h.pointer.fire('change');assert(!field.classes.has('ripple-ambient'));
 console.log('PASS ambient mobile visibility, offscreen, motion preferences, page lifecycle and desktop separation');
}
