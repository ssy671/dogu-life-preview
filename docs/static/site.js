(() => {
  'use strict';

  const readJSON = (id, fallback) => {
    const element = document.getElementById(id);
    if (!element) return fallback;
    try {
      return JSON.parse(element.textContent);
    } catch {
      return fallback;
    }
  };
  const koreanDate = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'
  });
  const dateKey = (value) => {
    const date = value instanceof Date ? value : new Date(value);
    if (!Number.isFinite(date.getTime())) return '';
    const parts = Object.fromEntries(koreanDate.formatToParts(date).map(({ type, value: part }) => [type, part]));
    return `${parts.year}-${parts.month}-${parts.day}`;
  };
  let today = dateKey(new Date());
  const rawPosts = readJSON('posts-data', []);
  const posts = Array.isArray(rawPosts) ? rawPosts.filter((post) => post && typeof post.slug === 'string') : [];
  const postBySlug = new Map(posts.map((post) => [post.slug, post]));
  const postDate = (post) => post && (post.date || dateKey(post.published_at));

  function updateBadges(root = document) {
    root.querySelectorAll('.new-badge').forEach((badge) => {
      const card = badge.closest('[data-slug]');
      const post = card && postBySlug.get(card.dataset.slug);
      const datedParent = badge.closest('[data-date], [data-published-date]');
      const published = badge.dataset.date || badge.dataset.publishedDate || postDate(post) ||
        (datedParent && (datedParent.dataset.date || datedParent.dataset.publishedDate));
      badge.hidden = published !== today;
    });
  }
  updateBadges();

  let refreshForDate = updateBadges;
  function checkDate() {
    const now = dateKey(new Date());
    if (today === now) return;
    today = now;
    refreshForDate();
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) checkDate();
  });
  window.setInterval(checkDate, 60000);

  const articleList = document.getElementById('article-list');
  // Article pages share this script for the date-sensitive NEW badge.
  if (!articleList) return;

  const viewData = readJSON('view-data', {});
  const counts = viewData && typeof viewData.counts === 'object' && viewData.counts !== null ? viewData.counts : {};
  const number = new Intl.NumberFormat('ko-KR');
  const countFor = (slug) => {
    const value = Object.prototype.hasOwnProperty.call(counts, slug) ? Number(counts[slug]) : 0;
    return Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0;
  };
  const nodes = new Map();
  articleList.querySelectorAll('article.card[data-slug]').forEach((card) => {
    if (!nodes.has(card.dataset.slug)) nodes.set(card.dataset.slug, card);
  });
  const seenSlugs = new Set();
  const availablePosts = posts.filter((post) => {
    if (!nodes.has(post.slug) || seenSlugs.has(post.slug)) return false;
    seenSlugs.add(post.slug);
    return true;
  });
  const timestamp = (post) => {
    const value = Date.parse(post.published_at);
    return Number.isFinite(value) ? value : 0;
  };
  const sequence = (post) => Number.isFinite(Number(post.sequence)) ? Number(post.sequence) : 0;
  const latestFirst = (a, b) => timestamp(b) - timestamp(a) || sequence(b) - sequence(a) ||
    (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0);
  const latest = [...availablePosts].sort(latestFirst);
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  const sortSelect = document.getElementById('sort-select');
  const todayFilter = document.getElementById('today-filter');
  const categoryTabs = Array.from(document.querySelectorAll('#category-tabs a[data-category]'));
  const resultCount = document.getElementById('result-count');
  const emptyState = document.getElementById('empty-state');
  const todayList = document.getElementById('today-list');
  const normalize = (value) => String(value || '').normalize('NFKC').toLocaleLowerCase('ko-KR');
  let state;
  let inputTimer;

  function updateViews(root) {
    root.querySelectorAll('article.card[data-slug]').forEach((card) => {
      const count = countFor(card.dataset.slug);
      card.querySelectorAll('.view-count').forEach((element) => {
        const valueElement = element.querySelector('[data-view-number], span');
        if (valueElement) valueElement.textContent = number.format(count);
        else element.textContent = `조회 ${number.format(count)}`;
      });
    });
  }

  function renderToday() {
    const todaysPosts = latest.filter((post) => postDate(post) === today);
    const hasToday = todaysPosts.length > 0;
    const featured = (hasToday ? todaysPosts : latest).slice(0, 3);
    if (todayList) {
      const fragment = document.createDocumentFragment();
      featured.forEach((post) => {
        const card = nodes.get(post.slug).cloneNode(true);
        card.hidden = false;
        // The repeated cards must not introduce duplicate document IDs.
        card.removeAttribute('id');
        card.querySelectorAll('[id]').forEach((element) => element.removeAttribute('id'));
        fragment.append(card);
      });
      todayList.replaceChildren(fragment);
      updateViews(todayList);
      updateBadges(todayList);
    }
    const heading = document.getElementById('today-heading');
    const description = document.getElementById('today-description');
    const link = document.getElementById('today-link');
    if (heading) heading.textContent = hasToday ? `오늘의 글 ${featured.length}편` : '최근에 발행한 글';
    if (description) description.textContent = hasToday
      ? '한국 시간 기준으로 오늘 발행된 글을 모았습니다. 일상에 필요한 작은 방법을 하나씩 만나보세요.'
      : '오늘 발행된 글이 없어 최근 글을 보여드립니다. 매일 오전 9시, 새로운 글을 준비합니다.';
    if (link) {
      link.textContent = hasToday ? `오늘의 글 ${featured.length}편 읽기 ↗` : '최근 글 읽기 ↗';
      link.setAttribute('href', todayList ? '#today-list' : '#articles');
    }
  }

  function readState() {
    const params = new URLSearchParams(window.location.search);
    return {
      q: params.get('q') || '',
      category: params.get('category') || '',
      sort: params.get('sort') === 'popular' ? 'popular' : 'latest',
      day: params.get('day') === 'today' ? 'today' : ''
    };
  }

  function stateURL(next, category = next.category) {
    const url = new URL(window.location.href);
    [['q', next.q.trim()], ['category', category], ['sort', next.sort === 'popular' ? 'popular' : ''], ['day', next.day]].forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    });
    url.hash = 'articles';
    return url;
  }

  function render() {
    if (searchInput && searchInput.value !== state.q) searchInput.value = state.q;
    if (sortSelect) sortSelect.value = state.sort;
    if (todayFilter) todayFilter.checked = state.day === 'today';
    categoryTabs.forEach((tab) => {
      const active = tab.dataset.category === state.category;
      tab.classList.toggle('active', active);
      if (active) tab.setAttribute('aria-current', 'true');
      else tab.removeAttribute('aria-current');
      const url = stateURL(state, tab.dataset.category);
      tab.href = `${url.pathname}${url.search}${url.hash}`;
    });
    const needle = normalize(state.q.trim());
    const ordered = state.sort === 'popular'
      ? [...latest].sort((a, b) => countFor(b.slug) - countFor(a.slug) || latestFirst(a, b))
      : latest;
    const fragment = document.createDocumentFragment();
    let visible = 0;
    ordered.forEach((post) => {
      const matches = (!state.category || post.category === state.category) &&
        (!state.day || postDate(post) === today) &&
        (!needle || normalize(`${post.title || ''} ${post.summary || ''} ${post.category || ''}`).includes(needle));
      const card = nodes.get(post.slug);
      card.hidden = !matches;
      if (matches) visible += 1;
      fragment.append(card);
    });
    articleList.replaceChildren(fragment);
    if (resultCount) resultCount.textContent = `${number.format(visible)}개의 글`;
    if (emptyState) emptyState.hidden = visible !== 0;
  }

  function changeState(patch) {
    clearTimeout(inputTimer);
    const next = { ...state, q: searchInput ? searchInput.value : state.q, ...patch };
    const url = stateURL(next);
    if (`${url.pathname}${url.search}${url.hash}` !== `${location.pathname}${location.search}${location.hash}`) {
      window.history.pushState(null, '', `${url.pathname}${url.search}${url.hash}`);
    }
    state = next;
    render();
  }

  if (searchForm) searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    changeState({ q: searchInput ? searchInput.value.trim() : '' });
  });
  if (searchInput) searchInput.addEventListener('input', () => {
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => changeState({}), 250);
  });
  if (sortSelect) sortSelect.addEventListener('change', () => changeState({ sort: sortSelect.value === 'popular' ? 'popular' : 'latest' }));
  if (todayFilter) todayFilter.addEventListener('change', () => changeState({ day: todayFilter.checked ? 'today' : '' }));
  categoryTabs.forEach((tab) => tab.addEventListener('click', (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    changeState({ category: tab.dataset.category });
  }));
  window.addEventListener('popstate', () => {
    clearTimeout(inputTimer);
    state = readState();
    render();
  });

  const viewsStatus = document.getElementById('views-status');
  if (viewsStatus) {
    const updated = viewData && viewData.updated_at ? new Date(viewData.updated_at) : null;
    if (updated && Number.isFinite(updated.getTime())) {
      const label = new Intl.DateTimeFormat('ko-KR', {
        timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false
      }).format(updated);
      viewsStatus.textContent = `조회수는 외부 집계 결과를 매시간 반영합니다. 마지막 반영: ${label} (한국 시간)`;
    } else {
      viewsStatus.textContent = '조회수 집계 준비 중 · 집계가 연결되면 매시간 반영합니다. 현재는 0으로 표시됩니다.';
    }
  }
  state = readState();
  updateViews(articleList);
  renderToday();
  render();

  refreshForDate = () => {
    updateBadges();
    renderToday();
    render();
  };
})();
