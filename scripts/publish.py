"""Publish at most three prepared articles once per Korea calendar day."""
import json
from datetime import datetime,time,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
KST=ZoneInfo('Asia/Seoul')

def release(root=ROOT,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(KST)
    read=lambda n:json.loads((root/'content'/n).read_text())
    posts=read('posts.json');queue=read('queue.json');state=read('state.json')
    today=now.date().isoformat()
    already_today=sum(datetime.fromisoformat(p['published_at']).astimezone(KST).date().isoformat()==today for p in posts)
    if now.hour<int(state.get('publish_hour',9)) or state.get('last_release_date','')>=today or already_today>=3:
        return {'published':0,'remaining':len(queue),'reason':'already released today or before publication hour'}
    known={p['slug'] for p in posts};queue=[p for p in queue if p['slug'] not in known]
    selected=queue[:int(state.get('daily_limit',3))]
    if len(selected)<3:
        return {'published':0,'remaining':len(queue),'reason':'not enough reviewed articles; replenish queue'}
    stamp=now.isoformat();sequence=max((p.get('sequence',0) for p in posts),default=0)
    for i,p in enumerate(selected):
        p=dict(p);p['published_at']=stamp;p['sequence']=sequence+i+1;posts.append(p)
    state['last_release_date']=today
    for name,data in [('posts.json',posts),('queue.json',queue[len(selected):]),('state.json',state)]:
        path=root/'content'/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(path)
    return {'published':len(selected),'remaining':len(queue)-len(selected),'date':today}

if __name__=='__main__':print(json.dumps(release(),ensure_ascii=False))
