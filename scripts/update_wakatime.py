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
# WakaTime reports AI chat time with no file, so its language is "Other"; the tool
# shows up as the editor instead. Normalise the names worth showing.
TOOLS={'claude code':'Claude Code','codex':'Codex','codex vscode':'Codex','vs code':'VS Code'}


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
    tools={}
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
        for row in day.get('editors',[]):
            name=TOOLS.get(str(row['name']).lower(),'Other')
            tools[name]=tools.get(name,0)+number(row['total_seconds'])
    if len(dates)!=7:
        raise ValueError('Incomplete seven-day summary')
    fields=('ai_input_tokens','ai_output_tokens','ai_additions','ai_prompt_events_total','ai_model_total_cost')
    ai={}
    for field in fields:
        values=[day['grand_total'].get(field) for day in payload['data']]
        ai[field]=sum(number(value) for value in values) if all(value is not None for value in values) else None
    return {'total_seconds':total,'start':start,'end':end,'days':sorted(days,key=lambda d:d['date']),'ai':ai,'languages':[
        {'name':name,'total_seconds':seconds,'percent':100*seconds/total if total else 0}
        for name,seconds in languages.items()],'tools':[
        {'name':name,'total_seconds':seconds,'percent':100*seconds/total if total else 0}
        for name,seconds in tools.items()]}


def save_cards(cards):
    assets=ROOT/'assets'
    assets.mkdir(exist_ok=True)
    readme=ROOT/'README.md'
    content=readme.read_text(encoding='utf-8')
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


HISTORY=ROOT/'assets'/'coding-history.json'
AI_FIELDS={'input':'ai_input_tokens','output':'ai_output_tokens','additions':'ai_additions',
           'prompts':'ai_prompt_events_total','cost':'ai_model_total_cost'}


def fetch(key,path,params=None):
    query=('?'+urlencode(params)) if params else ''
    request=Request('https://api.wakatime.com/api/v1/'+path+query,headers={
        'Authorization':'Basic '+base64.b64encode(key.encode()).decode(),
        'Accept':'application/json','User-Agent':'LZSMIAO-profile'})
    with urlopen(request,timeout=30) as response:
        if response.status==202:
            return None
        return json.load(response)


def day_record(day):
    """One day as the history keeps it: totals by language and by tool, and the AI
    figures. No project names: the history is public and projects may not be."""
    record={'date':day['range']['date'],'seconds':round(number(day['grand_total']['total_seconds']))}
    for field,rows,normalise in (('languages',day.get('languages',[]),label),
                                 ('tools',day.get('editors',[]),lambda name:TOOLS.get(str(name).lower(),'Other'))):
        totals={}
        for row in rows:
            name=normalise(row['name'])
            totals[name]=totals.get(name,0)+round(number(row['total_seconds']))
        record[field]={k:v for k,v in sorted(totals.items(),key=lambda kv:-kv[1]) if v>0}
    ai={}
    for short,field in AI_FIELDS.items():
        value=day['grand_total'].get(field)
        if value is not None:
            ai[short]=round(number(value),2)
    if ai:
        record['ai']=ai
    return record


def merge_history(history,payload):
    """Newer fetches replace a day; days that fall out of the API's window stay."""
    days={d['date']:d for d in history.get('days',[])}
    for day in payload.get('data',[]):
        record=day_record(day)
        if record['seconds']>0 or record['date'] in days:
            days[record['date']]=record
    return {'days':[days[k] for k in sorted(days)]}


def load_history():
    try:
        return json.loads(HISTORY.read_text())
    except (OSError,ValueError):
        return {'days':[]}


def backfill(key,history,before):
    """First run only: fetch everything from the account's first day, a month at a time."""
    profile=fetch(key,'users/current') or {}
    first=str(profile.get('data',{}).get('created_at',''))[:10]
    try:
        cursor=datetime.strptime(first,'%Y-%m-%d').date()
    except ValueError:
        return history
    while cursor<before:
        stop=min(before-timedelta(days=1),cursor+timedelta(days=29))
        try:
            payload=fetch(key,'users/current/summaries',{'start':str(cursor),'end':str(stop),'timezone':'Asia/Hong_Kong'})
        except (HTTPError,URLError,TimeoutError):
            break
        if payload:
            history=merge_history(history,payload)
        cursor=stop+timedelta(days=1)
    return history


def main():
    key=os.environ.get('WAKATIME_API_KEY','').strip()
    if not key:
        print('WAKATIME_API_KEY is not configured; cards unchanged.')
        return
    end=datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
    start=end-timedelta(days=6)
    payload=fetch(key,'users/current/summaries',{'start':str(start),'end':str(end),'timezone':'Asia/Hong_Kong'})
    if payload is None:
        print('WakaTime is calculating; cards unchanged.')
        return
    data=aggregate(payload,str(start),str(end))
    history=load_history()
    if not history['days']:
        history=backfill(key,history,start)
    HISTORY.write_text(json.dumps(merge_history(history,payload),ensure_ascii=False,separators=(',',':'))+'\n')
    cards={theme+('-mobile' if mobile else ''):card(data,theme,duration,label,mobile)
        for mobile in (False,True) for theme in ('light','dark')}
    cards.update({'report-'+theme+('-mobile' if mobile else ''):report(data,theme,duration,label,mobile)
        for mobile in (False,True) for theme in ('light','dark')})
    save_cards(cards)
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
