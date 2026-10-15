import json,time,urllib.request
from pathlib import Path
BASE='https://ssy671.github.io/dogu-life-preview/'
ROOT=Path(__file__).resolve().parents[1]
posts=json.loads((ROOT/'content/posts.json').read_text())
paths={'':('id="sort-select"','text/html'),'data/posts.json':('published_at','application/json'),'static/site.js':('popular','application/javascript'),'static/upgrade.css':('today','text/css')}
for p in posts:
 paths['post/'+p['slug']+'/']=(p['title'],'text/html')
 paths['static/diagrams/'+p['slug']+'.svg']=('<svg','image/svg+xml')
for attempt in range(1,13):
 try:
  for path,(expected,ctype) in paths.items():
   req=urllib.request.Request(BASE+path,headers={'Cache-Control':'no-cache','User-Agent':'Dogu-Life-Check/2.0'})
   with urllib.request.urlopen(req,timeout=20) as r:
    body=r.read().decode();assert expected in body,path
    if path=='':assert body.count('class="card" data-slug=')==len(posts)+min(3,len(posts)), 'Article list not yet updated'
    assert r.status==200,path
  print(f'PASS: homepage, sorting controls, data, {len(posts)} article pages and their SVG diagrams are live.')
  break
 except Exception as e:
  print(f'Attempt {attempt}: {e}',flush=True)
  if attempt==12:raise
  time.sleep(15)
