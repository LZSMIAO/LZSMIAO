"""Publish at most two public events, excluding this profile's update noise."""
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

README=Path(__file__).resolve().parents[1]/'README.md'
START='<!-- ACTIVITY:START -->'
END='<!-- ACTIVITY:END -->'
USER='LZSMIAO'


def activity(events):
    lines=[]
    seen=set()
    for event in events:
        if event.get('public') is not True:
            continue
        repo=event.get('repo',{}).get('name','')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo) or repo.lower()==f'{USER}/{USER}'.lower():
            continue
        payload=event.get('payload',{})
        kind=event.get('type')
        url=f'https://github.com/{repo}'
        if kind=='ReleaseEvent' and payload.get('action')=='published':
            url += '/releases'
            verb='發布版本'
        elif kind=='PullRequestEvent' and payload.get('action') in ('opened','closed'):
            pr=payload.get('pull_request',{})
            if payload['action']=='closed' and not pr.get('merged'):
                continue
            number=payload.get('number')
            if not isinstance(number,int):
                continue
            url += f'/pull/{number}'
            verb='合併 PR' if pr.get('merged') else '提交 PR'
        elif kind=='PushEvent':
            verb='更新程式'
        else:
            continue
        if url in seen:
            continue
        seen.add(url)
        date=str(event.get('created_at',''))[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):
            continue
        lines.append(f'- {date} · {verb} [{repo}]({url})')
        if len(lines)==2:
            break
    return '\n'.join(lines) or '<sub>暫無可展示的公開動態，之後會自動更新。</sub>'


def main():
    req=Request(f'https://api.github.com/users/{USER}/events/public?per_page=100',headers={
        'Accept':'application/vnd.github+json','User-Agent':f'{USER}-profile','X-GitHub-Api-Version':'2022-11-28'})
    # Unauthenticated public endpoint prevents private events from entering the feed.
    with urlopen(req,timeout=30) as response:
        events=json.load(response)
    if not isinstance(events,list):
        raise ValueError('Unexpected public events response')
    original=README.read_text()
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('Activity markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    updated=before+START+'\n'+activity(events)+'\n'+END+after
    if original!=updated:
        README.write_text(updated)
    print('Public activity updated.')


if __name__=='__main__':
    try:
        main()
    except Exception:
        print('Public activity unavailable; existing feed preserved.',file=sys.stderr)
        sys.exit(1)
