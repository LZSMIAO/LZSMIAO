"""Publish at most two public events, excluding this profile's update noise."""
import json
import hashlib
from html import escape
from functools import lru_cache
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
from typeface import ITALIC,faces

README=Path(__file__).resolve().parents[1]/'README.md'
START='<!-- ACTIVITY:START -->'
END='<!-- ACTIVITY:END -->'
USER='LZSMIAO'

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

def activity_card(repo, verb, date, dark=False, mobile=False, description=''):
    """The verb as a card title, like the other panels; the repository and a line
    about it underneath."""
    width,height=(480,100) if mobile else (880,98)
    pad=20 if mobile else 24
    bg,fg,muted,link=('#151b23','#f0f6fc','#b1bac4','#58a6ff') if dark else ('#f6f8fa','#1f2328','#59636e','#0969da')
    short=repo if len(repo)<=52 else repo[:49]+'…'
    if mobile:
        about=short_description(description,52)
        content=(f'<text x="{pad}" y="36" font-size="20" fill="{fg}" class="serif">{escape(verb)}</text>'
                 f'<text x="{width-pad}" y="35" fill="{muted}" font-size="12" text-anchor="end">{date}</text>'
                 f'<text x="{pad}" y="62" fill="{link}">{escape(short)}</text>'
                 +(f'<text x="{pad}" y="82" fill="{muted}" font-size="12">{escape(about)}</text>' if about else ''))
    else:
        about=short_description(description,max(0,100-len(short)))
        content=(f'<text x="{pad}" y="44" font-size="24" fill="{fg}" class="serif">{escape(verb)}</text>'
                 f'<text x="{width-pad}" y="43" fill="{muted}" font-size="12" text-anchor="end">{date}</text>'
                 f'<text x="{pad}" y="74"><tspan fill="{link}">{escape(short)}</tspan>'
                 +(f'<tspan dx="10" fill="{muted}" font-size="13">{escape(about)}</tspan>' if about else '')+'</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{escape(verb+": "+repo+(" — "+about if about else "")+" — "+date,quote=True)}">'
            f'<style>{faces("Chiron Italic")}.serif{{font-family:{ITALIC}}}</style>'
            f'<rect width="{width}" height="{height}" rx="12" fill="{bg}"/>'
            f'<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="14">{content}</g></svg>')

def activity_row(repo, verb, date, url, assets, description=''):
    paths={}
    for dark in (False,True):
        for mobile in (False,True):
            svg=activity_card(repo,verb,date,dark,mobile,description)
            path='assets/activity-'+hashlib.sha256(svg.encode()).hexdigest()[:12]+'.svg'
            if assets is not None:
                assets[path]=svg
            paths[dark,mobile]=path
    alt=escape(f'{verb}: {repo} — {date}',quote=True)
    return f'<a href="{url}"><picture><source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{paths[True,True]}"><source media="(max-width: 600px)" srcset="{paths[False,True]}"><source media="(prefers-color-scheme: dark)" srcset="{paths[True,False]}"><img src="{paths[False,False]}" alt="{alt}" width="100%"></picture></a>'

def activity(events, visibility_check=repository_is_public, assets=None, describe=None):
    # The live check and the About text come from the same cached request; a
    # caller that swaps in its own visibility check gets no network lookups.
    if describe is None:
        describe=repository_description if visibility_check is repository_is_public else (lambda repo: '')
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
            verb='Published release'
        elif kind=='PullRequestEvent' and payload.get('action') in ('opened','closed'):
            pr=payload.get('pull_request',{})
            if payload['action']=='closed' and not pr.get('merged'):
                continue
            number=payload.get('number')
            if not isinstance(number,int):
                continue
            url += f'/pull/{number}'
            verb='Merged PR' if pr.get('merged') else 'Opened PR'
        elif kind=='PushEvent':
            verb='Updated project'
        else:
            continue
        if url in seen:
            continue
        date=str(event.get('created_at',''))[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):
            continue
        if not visibility_check(repo):
            continue
        seen.add(url)
        lines.append(activity_row(repo,verb,date,url,assets,describe(repo)))
        if len(lines)==2:
            break
    return '\n'.join(lines) if lines else '<sub>No public activity to display yet. This section will update automatically.</sub>'

def update_content(original, events, assets=None):
    if START not in original and END not in original:
        section=r'(<summary><strong>Recent Activity</strong></summary>\s*<br>\s*)(<pre>.*?</pre>)(\s*</details>)'
        original,count=re.subn(section,lambda m:m[1]+START+'\n'+m[2]+'\n'+END+m[3],original,flags=re.S)
        if count!=1:
            raise ValueError('Cannot locate Recent Activity section')
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('Activity markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    return before+START+'\n'+activity(events, assets=assets)+'\n'+END+after

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
    print('Public activity updated.')

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(f'Public activity unavailable ({type(error).__name__}); existing feed preserved.',file=sys.stderr)
        sys.exit(1)
