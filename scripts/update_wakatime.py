"""Render the last seven calendar days, including today, in Asia/Hong_Kong."""
import base64
from datetime import datetime,timedelta
import json
import hashlib
import math
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
from coding_card import card
from weekly_report import card as report

ROOT=Path(__file__).resolve().parents[1]


def number(value):
    value=float(value)
    if not math.isfinite(value) or value<0:
        raise ValueError('Invalid duration')
    return value


def duration(seconds):
    minutes=int(number(seconds)//60)
    hours,minutes=divmod(minutes,60)
    return f'{hours}h {minutes:02d}m' if hours else (f'{minutes}m' if minutes else '<1m')


def label(value):
    return re.sub(r'[^\w .+#/-]','',str(value))[:24].strip() or 'Other'


def aggregate(payload,start,end):
    total=0
    languages={}
    dates=set()
    days=[]
    for day in payload['data']:
        date=day['range']['date']
        if not start<=date<=end or date in dates:
            raise ValueError('Unexpected date in summary')
        dates.add(date)
        seconds=number(day['grand_total']['total_seconds'])
        total+=seconds
        days.append({'date':date,'total_seconds':seconds})
        for row in day['languages']:
            name=label(row['name'])
            languages[name]=languages.get(name,0)+number(row['total_seconds'])
    if len(dates)!=7:
        raise ValueError('Incomplete seven-day summary')
    fields=('ai_input_tokens','ai_output_tokens','ai_additions','ai_prompt_events_total','ai_model_total_cost')
    ai={}
    for field in fields:
        values=[day['grand_total'].get(field) for day in payload['data']]
        ai[field]=sum(number(value) for value in values) if all(value is not None for value in values) else None
    return {'total_seconds':total,'start':start,'end':end,'days':sorted(days,key=lambda d:d['date']),'ai':ai,'languages':[
        {'name':name,'total_seconds':seconds,'percent':100*seconds/total if total else 0}
        for name,seconds in languages.items()]}


def overview(data):
    total=data['total_seconds']
    rows=sorted(data['languages'],key=lambda r:r['total_seconds'],reverse=True)[:4]
    rest=max(0,total-sum(r['total_seconds'] for r in rows))
    if rest:
        rows.append({'name':'Other','total_seconds':rest,'percent':100*rest/total})
    lines=['~~~text','📊 Last 7 days','','🕑 Time Zone: Asia/Hong Kong','',
           f"{data['start']} — {data['end']}",'','💬 Programming Languages:']
    for row in rows:
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])
        filled=round(row['percent']/4)
        bar='█'*filled+'░'*(25-filled)
        lines.append(f"{name:<20} {duration(row['total_seconds']):>10}  {bar} {row['percent']:5.1f}%")
    return '\n'.join(lines+['',f'Activity time: {duration(total)}','~~~'])


def save_cards(cards,data=None):
    assets=ROOT/'assets'
    assets.mkdir(exist_ok=True)
    readme=ROOT/'README.md'
    content=readme.read_text(encoding='utf-8')
    if data is not None:
        content,count=re.subn(r'~~~text\n📊 Last 7 days\n.*?\n~~~',lambda _:overview(data),content,flags=re.S)
        if count!=1:
            raise ValueError('Expected one activity overview block')
    keep=set()
    history_file=assets/'versions.json'
    history=json.loads(history_file.read_text()) if history_file.exists() else {}
    for theme,svg in cards.items():
        digest=hashlib.sha256(svg.encode()).hexdigest()[:12]
        stem=theme if theme.startswith('report-') else f'coding-{theme}'
        filename=f'{stem}-{digest}.svg'
        previous=history.get(stem,[])+sorted(p.name for p in assets.glob(stem+'-*.svg'))
        pattern_name=rf'{stem}-[a-f0-9]+\.svg'
        history[stem]=list(dict.fromkeys([filename]+[name for name in previous if re.fullmatch(pattern_name,name)]))[:8]
        keep.update(history[stem])
        (assets/filename).write_text(svg,encoding='utf-8')
        pattern=rf'assets/{stem}(?:-[a-f0-9]+)?\.svg(?:\?v=[a-f0-9]+)?'
        content=re.sub(pattern,'assets/'+filename,content)
    readme.write_text(content,encoding='utf-8')
    history_file.write_text(json.dumps(history,indent=2)+'\n')
    for old in assets.iterdir():
        if re.fullmatch(r'(?:coding|report)-(?:light|dark)(?:-mobile)?(?:-[a-f0-9]+)?\.svg',old.name) and old.name not in keep:
            old.unlink()


def main():
    key=os.environ.get('WAKATIME_API_KEY','').strip()
    if not key:
        print('WAKATIME_API_KEY is not configured; cards unchanged.')
        return
    end=datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
    start=end-timedelta(days=6)
    query=urlencode({'start':str(start),'end':str(end),'timezone':'Asia/Hong_Kong'})
    request=Request('https://api.wakatime.com/api/v1/users/current/summaries?'+query,headers={
        'Authorization':'Basic '+base64.b64encode(key.encode()).decode(),
        'Accept':'application/json','User-Agent':'LZSMIAO-profile'})
    with urlopen(request,timeout=30) as response:
        if response.status==202:
            print('WakaTime is calculating; cards unchanged.')
            return
        payload=json.load(response)
    data=aggregate(payload,str(start),str(end))
    cards={theme+('-mobile' if mobile else ''):card(data,theme,duration,label,mobile)
        for mobile in (False,True) for theme in ('light','dark')}
    cards.update({'report-'+theme+('-mobile' if mobile else ''):report(data,theme,duration,label,mobile)
        for mobile in (False,True) for theme in ('light','dark')})
    save_cards(cards,data)
    print('Updated coding cards with the last seven days, including today.')


if __name__=='__main__':
    try:
        main()
    except HTTPError as error:
        print(f'WakaTime HTTP {error.code}; cards unchanged.',file=sys.stderr)
        sys.exit(1)
    except (URLError,TimeoutError,ValueError,KeyError,TypeError,OSError):
        print('WakaTime unavailable or incomplete; cards unchanged.',file=sys.stderr)
        sys.exit(1)
