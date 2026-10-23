/* Decorative water rings only: no pointer coordinates are stored or transmitted. */
(() => {
  'use strict';
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const pointer = matchMedia('(hover: hover) and (pointer: fine)');
  if (!Element.prototype.animate) return;
  const MAX_RINGS = 8;
  const rings = new Set();
  const field = document.createElement('div');
  field.className = 'ripple-field';
  field.setAttribute('aria-hidden', 'true');
  document.body.prepend(field);
  const art = document.querySelector('.hero-art');
  const artField = art ? field.cloneNode(false) : null;
  if (artField) {
    artField.classList.add('ripple-field--art');
    art.prepend(artField);
  }
  let listening = false;
  let suspended = false;
  let lastTime = -Infinity;
  let lastX = -Infinity;
  let lastY = -Infinity;
  function clear() {
    for (const ring of rings) {
      ring.animation.cancel();
      ring.node.remove();
    }
    rings.clear();
    lastTime = lastX = lastY = -Infinity;
  }
  function move(event) {
    if (event.pointerType !== 'mouse' || event.buttons || rings.size >= MAX_RINGS) return;
    const now = performance.now();
    if (now - lastTime < 110 || Math.hypot(event.clientX - lastX, event.clientY - lastY) < 20) return;
    let target = field;
    let x = event.clientX;
    let y = event.clientY;
    // Only the empty page margins and illustration background are eligible.
    // Any text, control, image, iframe, ad, or nested element stays untouched.
    if (event.target === art && artField) {
      const rect = art.getBoundingClientRect();
      target = artField;
      x -= rect.left;
      y -= rect.top;
    } else if (event.target !== document.body && event.target !== document.documentElement) return;
    const node = document.createElement('span');
    node.className = 'water-ring';
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
    target.append(node);
    const animation = node.animate([
      { transform: 'translate(-50%, -50%) scale(.15)', opacity: 0 },
      { opacity: .28, offset: .16 },
      { transform: 'translate(-50%, -50%) scale(1)', opacity: 0 }
    ], { duration: 1200, easing: 'cubic-bezier(.16,.6,.35,1)' });
    const ring = { node, animation };
    rings.add(ring);
    animation.onfinish = () => { node.remove(); rings.delete(ring); };
    lastTime = now; lastX = event.clientX; lastY = event.clientY;
  }
  function sync() {
    const enabled = !motion.matches && pointer.matches && !document.hidden && !suspended;
    if (enabled !== listening) {
      document[enabled ? 'addEventListener' : 'removeEventListener']('pointermove', move, { passive: true });
      listening = enabled;
    }
    if (!enabled) clear();
  }
  motion.addEventListener('change', sync);
  pointer.addEventListener('change', sync);
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('resize', clear, { passive: true });
  window.addEventListener('pagehide', () => { suspended = true; sync(); });
  window.addEventListener('pageshow', () => { suspended = false; sync(); });
  sync();
})();
