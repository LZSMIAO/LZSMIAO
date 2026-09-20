"""Publish at most two public events, excluding this profile's update noise."""
import json
from functools import lru_cache
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

README=Path(__file__).resolve().parents[1]/'README.md'
START='<!-- ACTIVITY:START -->'
END='<!-- ACTIVITY:END -->'
USER='LZSMIAO'

@lru_cache(maxsize=100)
def repository_is_public(repo):
    # No authentication: private repositories cannot be returned by this request.
    req=Request(f'https://api.github.com/repos/{repo}',headers={
        'Accept':'application/vnd.github+json','User-Agent':f'{USER}-profile'})
    try:
        with urlopen(req,timeout=15) as response:
            metadata=json.load(response)
        return metadata.get('private') is False and metadata.get('visibility')=='public'
    except Exception:
        # Fail closed: never publish a repository whose visibility cannot be verified.
        return False

def activity(events, visibility_check=repository_is_public):
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
        lines.append(f'<tr><td width="100%">🛠️ <strong>{verb}</strong> · <a href="{url}">{repo}</a></td><td align="right" nowrap><code>{date}</code></td></tr>')
        if len(lines)==2:
            break
    return ('<table>\n<tbody>\n'+'\n'.join(lines)+'\n</tbody>\n</table>') if lines else '<sub>No public activity to display yet. This section will update automatically.</sub>'

def update_content(original, events):
    if START not in original and END not in original:
        section=r'(<summary><strong>Recent Activity</strong></summary>\s*<br>\s*)(<pre>.*?</pre>)(\s*</details>)'
        original,count=re.subn(section,lambda m:m[1]+START+'\n'+m[2]+'\n'+END+m[3],original,flags=re.S)
        if count!=1:
            raise ValueError('Cannot locate Recent Activity section')
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('Activity markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    return before+START+'\n'+activity(events)+'\n'+END+after

def main():
    req=Request(f'https://api.github.com/users/{USER}/events/public?per_page=100',headers={
        'Accept':'application/vnd.github+json','User-Agent':f'{USER}-profile','X-GitHub-Api-Version':'2022-11-28'})
    with urlopen(req,timeout=30) as response:
        events=json.load(response)
    if not isinstance(events,list):
        raise ValueError('Unexpected public events response')
    original=README.read_text()
    updated=update_content(original,events)
    if original!=updated:
        README.write_text(updated)
    print('Public activity updated.')

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(f'Public activity unavailable ({type(error).__name__}); existing feed preserved.',file=sys.stderr)
        sys.exit(1)
