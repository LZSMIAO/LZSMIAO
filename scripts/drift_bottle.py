"""One sentence from a visitor, kept on the page until the next one washes ashore."""
from datetime import datetime
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from unicodedata import east_asian_width,normalize
from zoneinfo import ZoneInfo
from ocean import ocean
from typeface import ITALIC,QUOTE,faces

ROOT=Path(__file__).resolve().parents[1]
README=ROOT/'README.md'
START='<!-- BOTTLE:START -->'
END='<!-- BOTTLE:END -->'
USER='LZSMIAO'
LIMIT=48
# Hand-set offsets for the opening quote (desktop, phone).
QX,QY,QX_M,QY_M=4,72,3,50
LOGIN=re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})')

THEMES={
    'light': dict(ink='#1f2328',muted='#59636e'),
    'dark': dict(ink='#f0f6fc',muted='#b1bac4'),
}


def columns(text):
    return sum(2 if east_asian_width(c) in 'WF' else 1 for c in text)


def sentence(body):
    """Keep the first real line only, stripped of anything that is not printable text."""
    for raw in str(body or '').splitlines():
        line=normalize('NFC',raw).strip()
        if not line or line.startswith('#') or line=='_No response_':
            continue
        # isprintable() is False for control, bidi-override and zero-width codepoints.
        line=' '.join(''.join(c for c in line if c.isprintable()).split())
        if not line:
            continue
        return line if len(line)<=LIMIT else line[:LIMIT-1].rstrip()+'…'
    return ''


def local_day(stamp):
    """GitHub stamps issues in UTC; the rest of this profile lives in Asia/Hong_Kong."""
    moment=datetime.strptime(str(stamp),'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=ZoneInfo('UTC'))
    return str(moment.astimezone(ZoneInfo('Asia/Hong_Kong')).date())


def wrap(text,budget):
    lines=[]
    current=''
    for ch in text:
        if columns(current)+columns(ch)>budget and current:
            cut=current.rfind(' ')
            if cut>len(current)//2:
                lines.append(current[:cut])
                current=current[cut+1:]
            else:
                lines.append(current)
                current=''
        current+=ch
    if current:
        lines.append(current)
    return lines[:3]


def card(text,login,day,theme,mobile=False):
    t=THEMES[theme]
    width=480 if mobile else 880
    # No frame: text sits on the column edge, like the page's own headings. The
    # right edge keeps two pixels so the italic credit's overhang is not clipped.
    pad=0
    size=18 if mobile else 22
    step=27 if mobile else 32
    first=60 if mobile else 72
    band=78 if mobile else 104
    # A message hangs off a large opening quote; the empty sea has nothing to quote.
    indent=(40 if mobile else 58) if text else 0
    rows=wrap(text,int((width-indent)/(size/2))) if text else []
    body=rows or ['No bottle has washed ashore yet.']
    top=first+(len(body)-1)*step+(18 if mobile else 22)
    height=top+band
    alt=f'{text} \u2014 @{login}' if text else 'No bottle has washed ashore yet'
    scene='An outlined bottle riding a sea of drifting swell lines' if text else 'An empty sea of drifting swell lines'
    label=19 if mobile else 23
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="bottle-title bottle-desc">',
           '<title id="bottle-title">Drift bottle</title>',
           f'<desc id="bottle-desc">{escape(alt+". "+scene+".")}</desc>',
           '<style>'+faces('Chiron Italic','Chiron Quote')+'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif}'
           f'.serif{{font-family:{ITALIC}}}.quote{{font-family:{QUOTE}}}</style>',
           ocean(width,height,top,theme,.8 if mobile else 1.0,bool(text)),
           f'<text x="{pad}" y="{27 if mobile else 31}" font-size="{label}" fill="{t["muted"]}" class="serif">Drift bottle</text>']
    if text:
        parts.append(f'<text x="{width-2}" y="{26 if mobile else 30}" font-size="{label-3}" fill="{t["muted"]}" '
                     f'text-anchor="end" class="serif">@{escape(login)} \u00b7 {day}</text>')
    if text:
        # A hairline mark at the face's lightest weight, in the muted ink: it sets
        # the line off as a quotation without outshouting it.
        parts.append(f'<text x="{pad-(QX_M if mobile else QX)}" y="{first+(QY_M if mobile else QY)}" '
                     f'font-size="{84 if mobile else 124}" fill="{t["muted"]}" fill-opacity=".6" class="quote">\u201c</text>')
    for i,row in enumerate(body):
        parts.append(f'<text x="{pad+indent}" y="{first+i*step}" font-size="{size}" font-weight="{600 if text else 400}" '
                     f'fill="{t["ink"] if text else t["muted"]}">{escape(row)}</text>')
    return ''.join(parts)+'</svg>\n'


def section(text,login,day,number,assets=None):
    paths={}
    for theme in ('light','dark'):
        for mobile in (False,True):
            svg=card(text,login,day,theme,mobile)
            path='assets/bottle-'+sha256(svg.encode()).hexdigest()[:12]+'.svg'
            if assets is not None:
                assets[path]=svg
            paths[theme,mobile]=path
    alt=escape(f'{text} — @{login}' if text else 'No bottle has washed ashore yet',quote=True)
    picture=(f'<picture>'
             f'<source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{paths["dark",True]}">'
             f'<source media="(max-width: 600px)" srcset="{paths["light",True]}">'
             f'<source media="(prefers-color-scheme: dark)" srcset="{paths["dark",False]}">'
             f'<img src="{paths["light",False]}" alt="{alt}" width="100%"></picture>')
    if number:
        return f'<a href="https://github.com/{USER}/{USER}/issues/{number}">{picture}</a>'
    return picture


def update_content(original,text,login,day,number,assets=None):
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('Bottle markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    return before+START+'\n'+section(text,login,day,number,assets)+'\n'+END+after


def main():
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    issue=event['issue']
    text=sentence(issue.get('body'))
    login=issue.get('user',{}).get('login','')
    if not text or not LOGIN.fullmatch(str(login)):
        raise ValueError('Nothing usable in this bottle')
    day=local_day(issue.get('created_at',''))
    assets={}
    original=README.read_text(encoding='utf-8')
    updated=update_content(original,text,login,day,issue.get('number'),assets)
    for path,svg in assets.items():
        (ROOT/path).write_text(svg,encoding='utf-8')
    README.write_text(updated,encoding='utf-8')
    # Only one bottle exists at a time, so every older rendering is dead weight.
    for old in (ROOT/'assets').glob('bottle-*.svg'):
        if re.fullmatch(r'bottle-[a-f0-9]+\.svg',old.name) and 'assets/'+old.name not in assets:
            old.unlink()
    print(f'Bottle from @{login} washed ashore.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as error:
        print(f'Bottle rejected ({type(error).__name__}); the page is unchanged.',file=sys.stderr)
        sys.exit(1)
