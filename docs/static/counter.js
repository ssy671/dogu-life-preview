(() => {
  if (new URLSearchParams(location.search).has('test')) return;
  if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return;
  document.querySelectorAll('[data-counter-src]').forEach(image => {
    image.src = image.dataset.counterSrc;
    image.addEventListener('error', () => { image.hidden = true; }, { once: true });
  });
})();
