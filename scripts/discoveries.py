"""Editorial discovery shelf. No products are published until evidence is supplied."""
import html
from datetime import date
from urllib.parse import urlsplit

CATEGORIES = {'desk': ('책상 소품', '작은 정리에도 취향을 담아요.', '케이블 정리 · 작은 수납 · 데스크 소품'),
              'keyboard': ('키보드 주변', '매일 손이 가는 자리의 작은 변화.', '손목 받침 · 청소 도구 · 주변 소품'),
              'display': ('작은 디스플레이', '필요한 정보를 귀엽게 한눈에.', '탁상 시계 · 미니 화면 · 정보 표시')}

def esc(value):
    return html.escape(str(value), quote=True)

def validate(data):
    if data.get('version') != 1 or not isinstance(data.get('items'), list):
        raise ValueError('Discovery data requires version 1 and an items list')
    seen = set()
    for item in data['items']:
        if not item.get('id') or item['id'] in seen:
            raise ValueError('Discovery IDs must be unique')
        seen.add(item['id'])
        if item.get('category') not in CATEGORIES or item.get('experience') not in ('used', 'found'):
            raise ValueError('Invalid discovery category or experience')
        for field in ('title', 'summary', 'source_url', 'checked_at'):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError('Missing discovery evidence: '+field)
        url = urlsplit(item['source_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password or any(c.isspace() for c in item['source_url']):
            raise ValueError('Discovery sources require a public HTTPS URL')
        if date.fromisoformat(item['checked_at']) > date.today():
            raise ValueError('Discovery check date cannot be in the future')
        if type(item.get('affiliate')) is not bool:
            raise ValueError('Affiliate relationship must be explicit')
        for field in ('pros', 'cons'):
            if not isinstance(item.get(field), list) or not item[field] or not all(isinstance(v,str) and v.strip() for v in item[field]):
                raise ValueError('Discovery requires stated advantages and limitations')
        if item['experience'] == 'used' and not item.get('usage_notes'):
            raise ValueError('Used items require usage notes')
    return data

def art(kind='desk'):
    shapes = {
        'desk': '<rect x="48" y="77" width="144" height="88" rx="24" fill="#e8bfa6"/><path d="M76 77V53m20 24V45m49 32V54m22 23V42"/><path d="M100 118h1m38 0h1m-31 14q12 12 24 0"/>',
        'keyboard': '<rect x="25" y="78" width="190" height="82" rx="22" fill="#d8dfb8"/><path d="M48 101h18m16 0h18m16 0h18m16 0h18m16 0h9M48 122h18m16 0h18m16 0h18m16 0h40M72 143h96"/><path d="M120 78V57q0-22 26-22h25"/>',
        'display': '<rect x="54" y="35" width="132" height="116" rx="26" fill="#c1d7cb"/><rect x="69" y="50" width="102" height="78" rx="16" fill="#f8f8f2"/><path d="M93 81h1m52 0h1m-41 16q14 13 28 0M106 153v18m28-18v18m-46 0h64"/>'}
    return '<svg class="discovery-art" viewBox="0 0 240 200" aria-hidden="true" focusable="false"><ellipse cx="120" cy="177" rx="95" ry="9" fill="#183e37" opacity=".08"/><g stroke="#36584c" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none">'+shapes[kind]+'</g></svg>'

def item_card(item):
    used = item['experience'] == 'used'
    badge = '직접 사용' if used else '미사용 발견'
    note = item.get('usage_notes', '') if used else '직접 사용하지 않았습니다. 아래 내용은 확인한 자료를 바탕으로 정리했습니다.'
    relation = '제휴 링크 · 구매 시 수수료를 받을 수 있습니다.' if item['affiliate'] else '제휴 관계 없음'
    rel = 'noopener noreferrer' + (' sponsored' if item['affiliate'] else '')
    lists = ''.join('<div><h3>'+label+'</h3><ul>'+''.join('<li>'+esc(v)+'</li>' for v in item[key])+'</ul></div>' for key,label in [('pros','좋은 점' if used else '자료에서 확인한 특징'),('cons','아쉬운 점' if used else '한계와 확인할 점')])
    return f'<article class="discovery-item"><span class="discovery-badge">{badge}</span><h2>{esc(item["title"])}</h2><p>{esc(item["summary"])}</p><p>{esc(note)}</p>{lists}<p>자료 확인일: <time>{esc(item["checked_at"])}</time> · {relation}</p><a href="{esc(item["source_url"])}" target="_blank" rel="{rel}">출처 확인하기 (새 탭)</a></article>'

def teaser(prefix):
    return f'<aside class="discovery-teaser" aria-labelledby="discovery-teaser-title"><div><span class="eyebrow">작은 취향, 새로운 코너</span><h2 id="discovery-teaser-title">귀여운 발견</h2><p>도움 되는 도구에, 갖고 싶은 귀여움 한 스푼.<br>책상 위 작은 소품을 천천히 골라볼게요.</p><a class="discovery-link" href="{prefix}discoveries/">준비 중인 코너 둘러보기 <span aria-hidden="true">↗</span></a></div>{art()}</aside>'

def page(data, prefix):
    validate(data)
    categories = ''.join(f'<article class="discovery-category">{art(key)}<span class="discovery-badge">탐색 예정</span><h3>{name}</h3><p>{desc}</p><small>{examples}</small></article>' for key,(name,desc,examples) in CATEGORIES.items())
    shelf = ''.join(item_card(item) for item in data['items']) if data['items'] else '<div class="discovery-empty"><span class="discovery-badge">첫 발견 준비 중</span><h2>아직 고르는 중이에요.</h2><p>귀엽다는 이유만으로 추천하지 않으려고요.<br>출처와 실제 쓰임을 확인한 소품부터 차근차근 담겠습니다.</p><p class="discovery-fine">현재 등록된 상품은 없습니다. 상품 링크·가격·사용 후기는 아직 제공하지 않습니다.</p></div>'
    return f'''<section class="discovery-intro"><span class="eyebrow">도구생활의 작은 취향</span><h1>귀여운 발견</h1><p class="discovery-lead">도움 되는 도구 + 갖고 싶은 귀여운 소품</p><p>매일 쓰는 자리에도 작은 즐거움이 필요하니까.<br>AliExpress에서 만나는 테크 소품을, 도구생활의 시선으로 살펴볼 공간입니다.</p><a class="discovery-link" href="#selection-guide">어떤 기준으로 고르나요? ↓</a></section><section aria-labelledby="discovery-categories"><div class="discovery-section-head"><h2 id="discovery-categories">이런 발견을 담을 거예요</h2><span>세 가지 관심사</span></div><div class="discovery-grid">{categories}</div><p class="discovery-fine">그림은 직접 만든 소품 모티프입니다. 실제 상품이나 판매 디자인을 나타내지 않습니다.</p></section><section class="discovery-shelf" aria-label="발견 목록">{shelf}</section><section class="discovery-guide" id="selection-guide" aria-labelledby="guide-title"><span class="eyebrow">고르는 마음</span><h2 id="guide-title">예쁨 다음에는, 쓰임을 봅니다.</h2><div class="discovery-guide-grid"><div><h3>01 · 출처부터 확인</h3><p>판매처와 확인일, 크기·연결 방식·호환성을 살펴봅니다. 사진은 사용 권한이 확인된 자료만 사용합니다.</p></div><div><h3>02 · 경험은 분명하게</h3><p><strong>직접 사용</strong>은 실제 경험과 장단점을, <strong>미사용 발견</strong>은 자료로 확인한 특징과 아직 모르는 점을 구분해 적습니다.</p></div><div><h3>03 · 관계도 투명하게</h3><p>제휴 링크가 생기면 해당 항목과 링크에 표시합니다. 광고는 편집 콘텐츠와 구분하며, 귀엽다는 이유로 품질을 단정하지 않습니다.</p></div></div></section><p class="discovery-return"><a class="discovery-link" href="{prefix}">← 도구생활 글 읽기로 돌아가기</a></p>'''
