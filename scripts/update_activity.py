"""Summarise recent public work as one card, with the full list on a page.

GitHub shows the card as one <img>, so it can carry a single link. It links to a
"Recent activity" page on the presence Worker, which reads assets/activity.json:
the public projects touched in the last 30 days (at most ten), each with its
latest action and the first sentence of its About text. This profile's own
update noise and anything not verifiably public are left out.
"""
import json
import hashlib
from html import escape
from functools import lru_cache
from pathlib import Path
import re
import sys
from datetime import date as calendar, datetime, timedelta
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from typeface import ITALIC,faces

README=Path(__file__).resolve().parents[1]/'README.md'
START='<!-- ACTIVITY:START -->'
END='<!-- ACTIVITY:END -->'
USER='LZSMIAO'
PAGE='https://projects.ism.tw'
WINDOW=30
LIMIT=10

@lru_cache(maxsize=100)
def repository(repo):
    # No authentication: private repositories cannot be returned by this request.
    req=Request(f'https://api.github.com/repos/{repo}',headers={
        'Accept':'application/vnd.github+json','User-Agent':f'{USER}-profile'})
    try:
        with urlopen(req,timeout=15) as response:
            return json.load(response)
    except Exception:
        return None

def repository_is_public(repo):
    metadata=repository(repo)
    # Fail closed: never publish a repository whose visibility cannot be verified.
    return bool(metadata) and metadata.get('private') is False and metadata.get('visibility')=='public'

def short_description(text, limit=90):
    """The first sentence of a repository's About text, cut at a word if still long."""
    text=' '.join(str(text or '').split())
    text=re.split(r'(?<=[.!?])\s|[。！？:：]',text,maxsplit=1)[0].strip().rstrip('.')
    if len(text)<=limit:
        return text
    cut=text[:limit-1]
    # Keep a word that ends exactly at the cut; otherwise back up to the last space.
    if text[limit-1]!=' ' and ' ' in cut:
        cut=cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;/-')+'…'

def repository_description(repo):
    return short_description((repository(repo) or {}).get('description'))

def activity_card(repo, verb, date, dark=False, mobile=False, description='', more=0, title='Recent activity'):
    """A card title like the other panels; the latest project and its About line under it."""
    width,height=(480,100) if mobile else (880,98)
    pad=20 if mobile else 24
    bg,fg,muted,link=('#151b23','#f0f6fc','#b1bac4','#58a6ff') if dark else ('#f6f8fa','#1f2328','#59636e','#0969da')
    short=repo if len(repo)<=52 else repo[:49]+'…'
    extra=f'<tspan dx="8" fill="{muted}" font-size="12">+{more} more</tspan>' if more else ''
    if mobile:
        about=short_description(description,52)
        content=(f'<text x="{pad}" y="36" font-size="20" fill="{fg}" class="serif">{escape(title)}</text>'
                 f'<text x="{width-pad}" y="35" fill="{muted}" font-size="12" text-anchor="end">{date}</text>'
                 f'<text x="{pad}" y="62" fill="{link}">{escape(short)}{extra}</text>'
                 +(f'<text x="{pad}" y="82" fill="{muted}" font-size="12">{escape(about)}</text>' if about else ''))
    else:
        about=short_description(description,max(0,92-len(short)))
        content=(f'<text x="{pad}" y="44" font-size="24" fill="{fg}" class="serif">{escape(title)}</text>'
                 f'<text x="{width-pad}" y="43" fill="{muted}" font-size="12" text-anchor="end">{date}</text>'
                 f'<text x="{pad}" y="74" fill="{link}">{escape(short)}{extra}</text>'
                 # The About line sits right, under the date, so the row reads as two columns.
                 +(f'<text x="{width-pad}" y="74" fill="{muted}" font-size="13" text-anchor="end">{escape(about)}</text>' if about else ''))
    label=f'{title}: {verb} {repo}'+(f' and {more} more' if more else '')+(f' — {about}' if about else '')+f' — {date}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{escape(label,quote=True)}">'
            f'<style>{faces("Chiron Italic")}.serif{{font-family:{ITALIC}}}</style>'
            f'<rect width="{width}" height="{height}" rx="12" fill="{bg}"/>'
            f'<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="14">{content}</g></svg>')

def activity_row(latest, more, assets):
    paths={}
    for dark in (False,True):
        for mobile in (False,True):
            svg=activity_card(latest['repo'],latest['verb'],latest['date'],dark,mobile,latest['description'],more)
            path='assets/activity-'+hashlib.sha256(svg.encode()).hexdigest()[:12]+'.svg'
            if assets is not None:
                assets[path]=svg
            paths[dark,mobile]=path
    alt=escape(f"Recent activity: {latest['repo']}"+(f' and {more} more' if more else '')+f" — {latest['date']}",quote=True)
    # One project needs no list: link straight to it. Two or more open the page.
    href=latest['url'] if not more else PAGE
    return f'<a href="{href}"><picture><source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{paths[True,True]}"><source media="(max-width: 600px)" srcset="{paths[False,True]}"><source media="(prefers-color-scheme: dark)" srcset="{paths[True,False]}"><img src="{paths[False,False]}" alt="{alt}" width="100%"></picture></a>'

def projects(events, visibility_check=repository_is_public, describe=None, today=None):
    """Public projects touched in the last WINDOW days, newest first, one row each."""
    # The live check and the About text come from the same cached request; a
    # caller that swaps in its own visibility check gets no network lookups.
    if describe is None:
        describe=repository_description if visibility_check is repository_is_public else (lambda repo: '')
    today=calendar.fromisoformat(today) if today else datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
    since=today-timedelta(days=WINDOW)
    rows=[]
    seen=set()
    for event in events:
        if event.get('public') is not True:
            continue
        repo=event.get('repo',{}).get('name','')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo) or repo.lower()==f'{USER}/{USER}'.lower() or repo.lower() in seen:
            continue
        payload=event.get('payload',{})
        kind=event.get('type')
        if kind=='ReleaseEvent' and payload.get('action')=='published':
            verb='Published release'
        elif kind=='PullRequestEvent' and payload.get('action') in ('opened','closed'):
            pr=payload.get('pull_request',{})
            if payload['action']=='closed' and not pr.get('merged'):
                continue
            verb='Merged PR' if pr.get('merged') else 'Opened PR'
        elif kind=='PushEvent':
            verb='Updated project'
        else:
            continue
        date=str(event.get('created_at',''))[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date) or calendar.fromisoformat(date)<since:
            continue
        if not visibility_check(repo):
            continue
        seen.add(repo.lower())
        rows.append({'repo':repo,'url':f'https://github.com/{repo}','verb':verb,'date':date,'description':describe(repo)})
        if len(rows)==LIMIT:
            break
    return rows

def activity(events, visibility_check=repository_is_public, assets=None, describe=None, today=None):
    rows=projects(events,visibility_check,describe,today)
    if assets is not None:
        # The page reads this; rows only ever describe verified-public repositories.
        assets['assets/activity.json']=json.dumps({'projects':rows},ensure_ascii=False,indent=2)+'\n'
    if not rows:
        return '<sub>No public activity to display yet. This section will update automatically.</sub>'
    return activity_row(rows[0],len(rows)-1,assets)

def update_content(original, events, assets=None, today=None):
    if START not in original and END not in original:
        section=r'(<summary><strong>Recent Activity</strong></summary>\s*<br>\s*)(<pre>.*?</pre>)(\s*</details>)'
        original,count=re.subn(section,lambda m:m[1]+START+'\n'+m[2]+'\n'+END+m[3],original,flags=re.S)
        if count!=1:
            raise ValueError('Cannot locate Recent Activity section')
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('Activity markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    return before+START+'\n'+activity(events, assets=assets, today=today)+'\n'+END+after

def main():
    req=Request(f'https://api.github.com/users/{USER}/events/public?per_page=100',headers={
        'Accept':'application/vnd.github+json','User-Agent':f'{USER}-profile','X-GitHub-Api-Version':'2022-11-28'})
    with urlopen(req,timeout=30) as response:
        events=json.load(response)
    if not isinstance(events,list):
        raise ValueError('Unexpected public events response')
    original=README.read_text()
    assets={}
    updated=update_content(original,events,assets)
    for path,svg in assets.items():
        (README.parent/path).write_text(svg)
    if original!=updated:
        README.write_text(updated)
    # Each redraw names new card files; drop the ones the README no longer shows.
    for old in (README.parent/'assets').glob('activity-*.svg'):
        if re.fullmatch(r'activity-[a-f0-9]+\.svg',old.name) and f'assets/{old.name}' not in updated:
            old.unlink()
    print('Public activity updated.')

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(f'Public activity unavailable ({type(error).__name__}); existing feed preserved.',file=sys.stderr)
        sys.exit(1)
