"""The profile's tagline, set as an SVG so it scales with the column.

As a Markdown heading it stayed at GitHub's fixed 24px while every card beside
it shrank on a phone, and it drew a rule underneath. Here the English is in the
serif italic and the Chinese in Chiron Sung HK.

The words live in tagline.txt at the repository root. Editing that file on
GitHub triggers .github/workflows/tagline.yml, which re-subsets the Chinese face
for the new characters and runs this script.
"""
from html import escape
from itertools import combinations
import json
from pathlib import Path
import re
import sys
from publish import publish
from typeface import ITALIC,TAGLINE,faces

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tagline.txt'
ADVANCES=json.loads((Path(__file__).resolve().parent/'fonts'/'italic-advances.json').read_text())
THEMES={
    'light': dict(ink='#1f2328',muted='#59636e'),
    'dark': dict(ink='#f0f6fc',muted='#b1bac4'),
}
# (size, line step) per line; the Chinese carries 1px of letter spacing.
ENGLISH_SET={False:(30,40),True:(27,36)}
CHINESE_SET=(17,28)
TRACKING=1
# A break after punctuation reads as a pause; anywhere else costs this much of
# the line width, so the wrap only breaks mid-phrase when nothing else fits.
PENALTY=.2
PAUSES=tuple(',;:.!?—–)')


def read(path=SOURCE):
    lines=[line.strip() for line in path.read_text(encoding='utf-8').splitlines()]
    lines=[line for line in lines if line and not line.startswith('#')]
    if len(lines)!=2:
        raise ValueError('tagline.txt needs exactly two lines: English, then Chinese')
    return lines[0],lines[1]


def plain(text):
    return ' '.join(part.strip() for part in text.split('|'))


def english_width(text,size):
    return sum(ADVANCES.get(ch,.5) for ch in text)*size


def chinese_width(text,size):
    return sum(.3 if ch==' ' else 1 if ord(ch)>0x2e7f else .55 for ch in text)*size+TRACKING*len(text)


def wrap(text,width,measure,pause):
    """Fewest lines that fit, then the most even of those, preferring pauses."""
    lines=[]
    for forced in (part.strip() for part in text.split('|')):
        words=forced.split(' ')
        for count in range(1,len(words)+1):
            best=None
            for cuts in combinations(range(1,len(words)),count-1):
                edges=(0,*cuts,len(words))
                rows=[' '.join(words[a:b]) for a,b in zip(edges,edges[1:])]
                widths=[measure(row) for row in rows]
                if max(widths)>width:
                    continue
                score=max(widths)+sum(0 if pause(row) else PENALTY*width for row in rows[:-1])
                if best is None or score<best[0]:
                    best=(score,rows)
            if best:
                lines+=best[1]
                break
        else:
            lines+=words
    return lines


def layout(english,chinese,mobile):
    width=(480 if mobile else 880)-8
    size,_=ENGLISH_SET[mobile]
    return (wrap(english,width,lambda row:english_width(row,size),lambda row:row.endswith(PAUSES)),
            wrap(chinese,width,lambda row:chinese_width(row,CHINESE_SET[0]),lambda row:True))


def card(theme,mobile=False,words=None):
    english,chinese=words or read()
    t=THEMES[theme]
    width=480 if mobile else 880
    top,bottom=layout(english,chinese,mobile)
    size,step=ENGLISH_SET[mobile]
    y=34
    parts=[]
    for line in top:
        parts.append(f'<text x="0" y="{y}" font-size="{size}" fill="{t["ink"]}" class="en">{escape(line)}</text>')
        y+=step
    y+=4
    for line in bottom:
        parts.append(f'<text x="1" y="{y}" font-size="{CHINESE_SET[0]}" fill="{t["muted"]}" class="zh" '
                     f'letter-spacing="{TRACKING}">{escape(line)}</text>')
        y+=CHINESE_SET[1]
    # Only a descender's worth below the last line, so the links sit close under it.
    height=y-CHINESE_SET[1]+6
    label=plain(english)+' '+plain(chinese)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(label,quote=True)}">'
            f'<style>{faces("Chiron Italic","Chiron Tagline")}.en{{font-family:{ITALIC}}}.zh{{font-family:{TAGLINE}}}</style>'
            +''.join(parts)+'</svg>\n')


def main():
    words=read()
    publish({'tagline-'+theme+('-mobile' if mobile else ''):card(theme,mobile,words)
             for mobile in (False,True) for theme in ('light','dark')})
    # Keep the fallback text in step with the image.
    readme=ROOT/'README.md'
    content=readme.read_text(encoding='utf-8')
    alt=escape(plain(words[0])+' '+plain(words[1]),quote=True)
    content,count=re.subn(r'<img alt="[^"]*"( src="assets/tagline-light-)',lambda m:f'<img alt="{alt}"'+m[1],content)
    if count!=1:
        raise ValueError('README does not show the tagline')
    readme.write_text(content,encoding='utf-8')
    print('Tagline redrawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Tagline unchanged ({type(error).__name__}: {error}).',file=sys.stderr)
        sys.exit(1)
