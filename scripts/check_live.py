import json,os,time,urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
BASE=os.getenv('BLOG_CHECK_URL','https://ssy671.github.io/dogu-life-preview/').strip().rstrip('/')+'/'
ROOT=Path(__file__).resolve().parents[1]
posts=json.loads((ROOT/'content/posts.json').read_text())
manifest=ROOT/'content/illustrations.json'
illustrations=json.loads(manifest.read_text()) if manifest.exists() else {}
published_illustrations={p['slug']:illustrations[p['slug']] for p in posts if p['slug'] in illustrations}
image_paths={details['file'] for details in published_illustrations.values()}
class InlineImageParser(HTMLParser):
 def __init__(self):
  super().__init__();self.stack=[];self.images=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='img' and any(t=='div' and 'prose' in c for t,c in self.stack) and any(t=='figure' and 'article-illustration' in c for t,c in self.stack):
   self.images.append(attrs.get('src'))
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
   self.stack.append((tag,attrs.get('class','').split()))
 def handle_endtag(self,tag):
  for index in range(len(self.stack)-1,-1,-1):
   if self.stack[index][0]==tag:
    del self.stack[index:];break
def check_raster(path,body,ctype):
 suffix=Path(path).suffix.lower()
 expected={'.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.avif':'image/avif'}[suffix]
 assert ctype==expected,f'{path}: expected {expected}, got {ctype}'
 assert len(body)>12,f'{path}: empty or truncated image'
 if suffix=='.webp':valid=body[:4]==b'RIFF' and body[8:12]==b'WEBP'
 elif suffix=='.png':valid=body[:8]==b'\x89PNG\r\n\x1a\n'
 elif suffix in {'.jpg','.jpeg'}:valid=body[:3]==b'\xff\xd8\xff'
 else:valid=body[4:8]==b'ftyp' and any(brand in body[8:40] for brand in (b'avif',b'avis'))
 assert valid,f'{path}: response is not a valid {suffix} image signature'
paths={'':('id="sort-select"','text/html'),'data/posts.json':('published_at','application/json'),'static/site.js':('popular','application/javascript'),'static/upgrade.css':('today','text/css')}
for p in posts:
 paths['post/'+p['slug']+'/']=(p['title'],'text/html')
 paths['static/diagrams/'+p['slug']+'.svg']=('<svg','image/svg+xml')
for path in sorted(image_paths):paths[path]=(None,None)
article_images={'post/'+slug+'/':urlsplit(BASE).path+details['file'] for slug,details in published_illustrations.items()}
for attempt in range(1,13):
 try:
  for path,(expected,ctype) in paths.items():
   req=urllib.request.Request(BASE+path,headers={'Cache-Control':'no-cache','User-Agent':'Dogu-Life-Check/2.0'})
   with urllib.request.urlopen(req,timeout=20) as r:
    assert r.status==200,path
    payload=r.read()
    if path in image_paths:check_raster(path,payload,r.headers.get_content_type())
    else:
     body=payload.decode('utf-8');assert expected in body,path
     if path=='':assert body.count('class="card" data-slug=')==len(posts)+min(3,len(posts)), 'Article list not yet updated'
     if path in article_images:
      parser=InlineImageParser();parser.feed(body)
      assert article_images[path] in parser.images,f'{path}: mapped illustration missing from article body'
  print(f'PASS: {BASE} homepage, sorting controls, data, {len(posts)} article pages, their SVG diagrams and {len(image_paths)} generated raster illustrations are live.')
  break
 except Exception as e:
  print(f'Attempt {attempt}: {e}',flush=True)
  if attempt==12:raise
  time.sleep(15)
