/* Dependency-free regression checks for the exact helpers shipped in site.js. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, '../docs/static/site.js'), 'utf8');
const begin = script.indexOf('  const normalize =');
const end = script.indexOf('  let state;', begin);
assert.ok(begin >= 0 && end > begin);
function element(tag = 'p') {
  return {
    tag, children: [], classes: new Set(),
    set innerHTML(value) { throw new Error('Search must never render HTML'); },
    append(...children) { this.children.push(...children); },
    replaceChildren(fragment) { this.children = fragment.children; },
    classList: { toggle() {} },
    set textContent(value) { this.children = [value]; },
    get textContent() { return this.children.map(child => typeof child === 'string' ? child : child.textContent).join(''); },
  };
}
const posts = [{slug: 'one', title: '안전한 제목', summary: '소개', category: '도구 활용', body: '## 본문\n\n앞 문장 <img src=x onerror=alert(1)> ＡＢＣ 뒤 문장'}];
const api = vm.runInNewContext(`${script.slice(begin, end)}\n({ searchable, matchRanges, highlight, renderCardText, searchIndex });`, {
  availablePosts: posts,
  document: {createDocumentFragment: () => element('fragment'), createElement: element},
  Intl, Map, String, Array,
});
const ranges = (text, query) => JSON.parse(JSON.stringify(api.matchRanges(api.searchable(text), query)));
assert.deepEqual(ranges('ＡＢＣ abc', 'abc'), [[0, 3], [4, 7]]);
assert.deepEqual(ranges('가나다', '가'), [[0, 2]]);
assert.deepEqual(ranges('ﬃ', 'f'), [[0, 1]]); // NFKC expansion does not duplicate marks.
assert.deepEqual(ranges('İab', 'ab'), [[1, 3]]); // Lowercase expansion preserves offsets.
assert.deepEqual(ranges('literal [.*] and [.*]', '[.*]'), [[8, 12], [17, 21]]);
assert.deepEqual(ranges('anything', ''), []);
assert.deepEqual(ranges('아무 글', '찾을 수 없는 말'), []);
const target = element();
api.highlight(target, api.searchable('<img src=x onerror=alert(1)>'), '<img');
assert.equal(target.textContent, '<img src=x onerror=alert(1)>');
assert.equal(target.children.filter(child => typeof child !== 'string').length, 1);
assert.equal(target.children[1].tag, 'mark');
assert.equal(target.children[1].textContent, '<img');
api.highlight(target, api.searchable('안전한 일반 문장'), '<script>alert(1)</script>');
assert.equal(target.textContent, '안전한 일반 문장');
assert.equal(target.children.some(child => child.tag === 'mark'), false);
const context = '앞'.repeat(240) + '희귀검색어' + '뒤'.repeat(240);
api.highlight(target, api.searchable(context), '희귀검색어', true);
assert.ok(target.textContent.startsWith('…') && target.textContent.endsWith('…'));
assert.ok(target.textContent.includes('희귀검색어'));
assert.ok(target.textContent.length < 180);
const title = element('h3'), category = element('span'), summary = element('p');
const card = { querySelector: selector => ({h3: title, '.eyebrow': category, '.card-copy p': summary}[selector]) };
api.renderCardText(card, posts[0], 'abc');
assert.ok(summary.textContent.includes('ＡＢＣ'));
assert.ok(summary.children.some(child => child.tag === 'mark' && child.textContent === 'ＡＢＣ'));
api.renderCardText(card, posts[0]);
assert.equal(summary.textContent, '소개');
assert.equal(summary.children.some(child => child.tag === 'mark'), false);
assert.equal(api.searchIndex.get('one').body.normalized.includes('abc'), true);
console.log('Search regression checks passed: normalized matching, offsets, context, literal/XSS-safe marks, reset.');
