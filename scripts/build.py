"""Render the blog and topic-specific SVG diagrams; no server or packages required."""
import argparse,html,json,math,re,os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
IS_CLOUDFLARE=bool(os.getenv('CF_PAGES'))
SITE=os.getenv('BLOG_SITE_URL', os.getenv('CF_PAGES_URL','') if IS_CLOUDFLARE else '') or 'https://ssy671.github.io/dogu-life-preview'
SITE=SITE.rstrip('/')
BASE_PATH=os.getenv('BLOG_BASE_PATH', '/' if IS_CLOUDFLARE else '/dogu-life-preview/')
PREFIX='/' + BASE_PATH.strip('/') + '/' if BASE_PATH.strip('/') else '/'
VIEWS_SOURCE=os.getenv('BLOG_VIEWS_URL','https://raw.githubusercontent.com/ssy671/dogu-life-preview/main/content/views.json' if IS_CLOUDFLARE else '')
KST=ZoneInfo('Asia/Seoul')
CATEGORIES=['디지털 정리','업무 습관','도구 활용']

def esc(value):return html.escape(str(value),quote=True)
def dump(value):return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
def load(path):return json.loads((ROOT/path).read_text())
def day(post):return datetime.fromisoformat(post['published_at']).astimezone(KST).date().isoformat()
def order(post):return (datetime.fromisoformat(post['published_at']).timestamp(),post['sequence'],post['slug'])
def figure(post):return PREFIX+'static/diagrams/'+post['slug']+'.svg'
def minutes(post):return max(1,math.ceil(len(post['body'])/600))
def public(post):return {k:post[k] for k in ['slug','title','category','summary','published_at','sequence']}|{'date':day(post),'reading_minutes':minutes(post)}

def icon(kind,x,y):
    shapes={
      'folder':'<path d="M8 28V14h29l10 12h42v50H8z"/><path d="M8 28h81"/>',
      'calendar':'<rect x="10" y="16" width="76" height="64" rx="7"/><path d="M10 36h76M28 8v17M67 8v17M28 51h11M56 51h11M28 65h11"/>',
      'document':'<path d="M20 5h42l16 17v64H20zM62 5v18h16M32 39h34M32 52h34M32 65h24"/>',
      'search':'<circle cx="40" cy="38" r="25"/><path d="m58 57 22 22M29 38h22M40 27v22"/>',
      'check':'<rect x="13" y="12" width="68" height="68" rx="10"/><path d="m27 45 15 15 27-31"/>',
      'clock':'<circle cx="48" cy="45" r="34"/><path d="M48 23v24l18 10"/>',
      'link':'<path d="m37 52-8 8a16 16 0 0 1-23-23l17-17a16 16 0 0 1 23 0m0 18 8-8a16 16 0 0 1 23 23L60 70a16 16 0 0 1-23 0M30 46l25-25"/>',
      'chart':'<path d="M12 77h74M24 76V49h15v27M47 76V29h15v47M70 76V11h15v65"/>',
    }
    return f'<g transform="translate({x} {y})" fill="none" stroke="#183e37" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{shapes[kind]}</g>'

def diagram(post):
    category=post['category'];labels=post.get('diagram_labels',['목적 살펴보기','작게 실행하기','결과 돌아보기'])
    color={'디지털 정리':'#e7eedc','업무 습관':'#e0ebe7','도구 활용':'#eee7da'}[category]
    kinds={'디지털 정리':['search','folder','check'],'업무 습관':['document','calendar','check'],'도구 활용':['document','search','check']}[category]
    slug=post['slug']
    if any(x in slug for x in ['time','day','calendar','deadline','notification']):kinds=['clock','calendar','check']
    elif any(x in slug for x in ['link','bookmark','reference']):kinds=['link','search','folder']
    elif any(x in slug for x in ['sheet','chart','comparison']):kinds=['document','chart','check']
    desc=' → '.join(labels)
    text=f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="480" viewBox="0 0 960 480" role="img" aria-labelledby="title desc"><title id="title">{esc(post["title"])}</title><desc id="desc">{esc(desc)}</desc><rect width="960" height="480" fill="{color}"/><circle cx="912" cy="52" r="112" fill="#d8ef89" opacity=".5"/><g font-family="Noto Sans KR,Malgun Gothic,Apple SD Gothic Neo,sans-serif" fill="#183e37"><text x="48" y="57" font-size="16" letter-spacing="3">도구생활 · {esc(category)}</text><text x="48" y="103" font-size="29" font-weight="700">작게 시작하는 세 가지 단계</text>'
    for i,label in enumerate(labels):
        x=48+i*304
        text+=f'<rect x="{x}" y="146" width="256" height="260" rx="18" fill="#fffef8"/><circle cx="{x+37}" cy="181" r="15" fill="#d8ef89"/><text x="{x+37}" y="187" text-anchor="middle" font-size="15" font-weight="700">{i+1}</text>'+icon(kinds[i],x+80,214)+f'<text x="{x+128}" y="352" text-anchor="middle" font-size="21" font-weight="600">{esc(label)}</text>'
        if i<2:text+=f'<path d="M{x+266} 273h26m-8-8 8 8-8 8" fill="none" stroke="#183e37" stroke-width="3"/>'
    return text+'</g></svg>'

def prose(body):
    return ''.join('<h2>'+esc(b[3:])+'</h2>' if b.startswith('## ') else '<p>'+esc(b).replace('\n','<br>')+'</p>' for b in body.strip().split('\n\n'))

def shell(title,body,description='',article=None):
    head=''
    if article:
        url=SITE+'/post/'+article['slug']+'/'
        data={'@context':'https://schema.org','@type':'BlogPosting','headline':article['title'],'description':article['summary'],'datePublished':article['published_at'],'author':{'@type':'Organization','name':'도구생활'},'image':SITE+'/static/diagrams/'+article['slug']+'.svg','mainEntityOfPage':url}
        head=f'<link rel="canonical" href="{esc(url)}"><script type="application/ld+json">{dump(data)}</script>'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · 도구생활</title><meta name="description" content="{esc(description or '디지털 생활과 업무를 가볍게 만드는 도구 활용 가이드')}"><meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#183e37"><link rel="stylesheet" href="{PREFIX}static/style.css"><link rel="stylesheet" href="{PREFIX}static/upgrade.css">{head}<script defer src="{PREFIX}static/site.js"></script><script defer src="{PREFIX}static/counter.js"></script></head><body data-views-source="{esc(VIEWS_SOURCE)}"><header><a class="brand" href="{PREFIX}">도구생활<span>TOOLS FOR EVERYDAY</span></a><nav><a href="{PREFIX}">글 읽기</a><a href="{PREFIX}about/">소개</a></nav></header><main>{body}</main><footer><div><b>도구생활</b><p>복잡한 디지털 일상을, 한 편의 글로 가볍게.</p></div><div><a href="{PREFIX}privacy/">개인정보 처리방침</a> · <a href="{PREFIX}contact/">문의</a><p>© {datetime.now(KST).year} 도구생활</p></div></footer></body></html>'''

def card(post,views,today):
    count=views.get('counts',{}).get(post['slug'],0);date=day(post);badge='' if date==today else ' hidden'
    return f'''<article class="card" data-slug="{esc(post['slug'])}" data-date="{date}" data-published-at="{esc(post['published_at'])}" data-sequence="{post['sequence']}"><a href="{PREFIX}post/{esc(post['slug'])}/"><div class="card-art"><img src="{figure(post)}" alt="{esc(post['title'])}의 핵심 흐름" width="960" height="480" loading="lazy"></div><div class="card-copy"><div class="card-labels"><span class="eyebrow">{esc(post['category'])}</span><span class="new-badge" data-date="{date}"{badge}>NEW</span></div><h3>{esc(post['title'])}</h3><p>{esc(post['summary'])}</p><div class="meta card-footer"><span>{date} · {minutes(post)}분 읽기</span><span class="view-count">조회 {count:,}</span></div></div></a></article>'''

def home(posts,views,now):
    ordered=sorted(posts,key=order,reverse=True);today=now.astimezone(KST).date().isoformat();fresh=[p for p in ordered if day(p)==today][:3]
    featured=fresh or ordered[:3];heading='오늘의 글' if fresh else '최근 글';cta='오늘의 글 3편 읽기 ↗' if fresh else '최근 글 읽기 ↗'
    hero=f'''<section class="hero"><div><span class="eyebrow">DIGITAL LIFE, SIMPLIFIED</span><h1>도구는 덜 복잡하게.<br>일상은 더 여유롭게.</h1><p>파일 정리부터 집중하는 업무 습관까지.<br>매일 오전 9시, 새로운 글 세 편으로 만나세요.</p><a id="today-link" class="button" href="#today-list">{cta}</a></div><div class="hero-art"><span class="orbit">↗</span><div class="note"><small>작은 변화, 큰 여유</small><strong>정리하고.<br>집중하고.<br>가볍게.</strong><span>YOUR EVERYDAY TOOLKIT</span></div><i class="dot"></i></div></section>'''
    hero+=f'''<section class="today-section" aria-labelledby="today-heading"><div class="section-head"><div><span class="eyebrow">DAILY THREE</span><h2 id="today-heading">{heading}</h2><p id="today-description">하루에 세 편, 오늘 적용할 수 있는 작은 방법을 읽어보세요.</p></div></div><div class="articles" id="today-list">{''.join(card(p,views,today) for p in featured)}</div></section>'''
    tabs=''.join(f'<a class="{"active" if not cat else ""}" data-category="{esc(cat)}" href="?category={esc(cat)}#articles">{cat or "전체 글"}</a>' for cat in ['']+CATEGORIES)
    body=hero+f'''<section id="articles"><div class="section-head"><div><span class="eyebrow">THE JOURNAL</span><h2>일상을 바꾸는 읽을거리</h2></div><form id="search-form" class="search"><input id="search-input" name="q" aria-label="글 검색" placeholder="궁금한 도구나 습관 검색"><button>검색</button></form></div><div class="categories" id="category-tabs">{tabs}</div><div class="browse-toolbar"><div class="browse-controls"><label class="sort-control" for="sort-select">정렬 <select id="sort-select"><option value="latest">최신순</option><option value="popular">인기순</option></select></label><label class="today-control"><input id="today-filter" type="checkbox"> 오늘 올라온 글만</label></div><span id="result-count" role="status">{len(posts)}편의 글</span></div><p id="views-status" class="views-status">조회수 집계 준비 중입니다.</p><div class="articles" id="article-list">{''.join(card(p,views,today) for p in ordered)}</div><p id="empty-state" class="empty" role="status" hidden>조건에 맞는 글이 없습니다. 검색어나 분류를 바꿔 보세요.</p></section><aside class="callout"><span>한 번에 하나씩</span><h2>좋은 도구보다 중요한 건,<br>나에게 맞는 사용법입니다.</h2><p>도구생활은 새로운 앱을 더하는 대신, 이미 가진 도구를 잘 쓰는 방법을 이야기합니다.</p></aside><script id="posts-data" type="application/json">{dump([public(p) for p in posts])}</script><script id="view-data" type="application/json">{dump(views)}</script>'''
    return shell('디지털 일상을 가볍게',body)

def article(post,posts,views):
    date=day(post);count=views.get('counts',{}).get(post['slug'],0);labels=' → '.join(post['diagram_labels'])
    art=''
    if post['slug']=='organize-work-folders':art=f'<figure class="post-figure"><img src="{PREFIX}static/organize-folders.webp" alt="진행 중인 자료와 보관 자료를 두 서류함으로 나눈 그림" width="1536" height="1024" loading="lazy"><figcaption>진행 자료와 보관 자료의 자리를 나눠 봅니다.</figcaption></figure>'
    chunks=post['body'].split('\n\n');pivot=next((i for i in range(2,len(chunks)) if chunks[i].startswith('## ')),len(chunks))
    text=prose('\n\n'.join(chunks[:pivot]))+f'<figure class="post-figure"><img src="{figure(post)}" alt="{esc(labels)}" width="960" height="480" loading="lazy"><figcaption>{esc(labels)}</figcaption></figure>'+prose('\n\n'.join(chunks[pivot:]))
    related=[p for p in sorted(posts,key=order,reverse=True) if p['category']==post['category'] and p['slug']!=post['slug']][:3]
    links=''.join(f'<li><a href="{PREFIX}post/{p["slug"]}/">{esc(p["title"])}</a></li>' for p in related)
    body=f'''<article class="reading"><a href="{PREFIX}#articles">← 전체 글</a><span class="eyebrow">{esc(post['category'])}</span><h1>{esc(post['title'])}</h1><p class="lead">{esc(post['summary'])}</p><div class="meta reading-meta"><span>도구생활 편집부 · {date} · {minutes(post)}분 읽기</span><span class="new-badge" data-date="{date}" hidden>NEW</span><span class="view-count">조회 {count:,} <small>(매시간 반영)</small></span></div>{art}<div class="prose">{text}</div><div class="article-counter"><img data-counter-src="https://hits.sh/ssy671.github.io/dogu-life-preview/post/{post['slug']}.svg?label=views&amp;color=183e37" alt="이 글의 누적 조회수" width="92" height="20" referrerpolicy="no-referrer"><p>조회수는 외부 서비스로 집계하며 새로고침·봇 요청이 포함될 수 있습니다.</p></div><aside class="related-posts"><h2>함께 읽으면 좋은 글</h2><ul>{links}</ul></aside></article>'''
    return shell(post['title'],body,post['summary'],post)

def build(now=None):
    now=now or datetime.now(timezone.utc);posts=load('content/posts.json');views=load('content/views.json');docs=ROOT/'docs'
    assert len({p['slug'] for p in posts})==len(posts),'Duplicate slug'
    for p in posts:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug'])
        assert p['category'] in CATEGORIES and len(p['diagram_labels'])==3
        assert datetime.fromisoformat(p['published_at'])<=now,'Future article cannot be published'
    diagrams=docs/'static/diagrams';diagrams.mkdir(parents=True,exist_ok=True)
    for p in posts:
        (diagrams/(p['slug']+'.svg')).write_text(diagram(p))
        target=docs/'post'/p['slug']/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(article(p,posts,views))
    (docs/'index.html').write_text(home(posts,views,now))
    (docs/'data').mkdir(exist_ok=True)
    (docs/'data/posts.json').write_text(dump([public(p) for p in posts]))
    (docs/'data/views.json').write_text(dump(views))
    privacy='''## 현재 사용하는 정보\n\n이 사이트에는 독자 회원가입과 댓글 기능이 없습니다. 글의 인기도를 보여 주기 위해 hits.sh의 공개 조회수 카운터를 사용합니다. 글을 열면 해당 서비스에 이미지 요청이 전송되며 글의 경로와 접속 IP, 브라우저 요청 정보가 전달될 수 있습니다. 카운터는 고유 독자 수가 아닌 이미지 요청 수를 바탕으로 하며 새로고침이나 자동 요청이 포함될 수 있습니다.\n\n## 집계와 외부 서비스\n\n글별 누적 조회수는 공개된 값이며 매시간 사이트에 반영합니다. 외부 서비스가 응답하지 않으면 마지막으로 확인한 집계를 유지합니다. 브라우저의 추적 방지 설정에 따라 집계되지 않을 수 있습니다. 글꼴을 불러올 때 Google Fonts에 요청이 전송될 수 있습니다. 광고와 결제 서비스는 연결되어 있지 않습니다.\n\n## 운영 안내\n\n콘텐츠 오류와 개인정보 관련 문의 경로는 문의 페이지를 참고해 주세요. 외부 서비스의 최신 처리 정책은 각 제공자의 안내를 확인해 주세요.'''
    privacy_body=f'<section class="reading"><h1>개인정보 처리 안내</h1><div class="prose">{prose(privacy)}<p><a href="https://hits.sh/" rel="noreferrer">hits.sh 서비스 안내</a></p></div></section>'
    (docs/'privacy').mkdir(exist_ok=True);(docs/'privacy/index.html').write_text(shell('개인정보 처리 안내',privacy_body))
    for name in ['about','contact']:
        path=docs/name/'index.html'
        if path.exists():
            path.write_text(path.read_text().replace('/dogu-life-preview/',PREFIX))
    (docs/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    return len(posts)

if __name__=='__main__':
    print(f'Built {build()} published articles and their illustrations.')
