"""A typographic closing composition, with words edited only in end-word.md."""
from hashlib import sha256
from html import escape
from pathlib import Path
import re
import sys
from typeface import END_WORD,ITALIC,faces
from tagline import chinese_width

ROOT=Path(__file__).resolve().parents[1]
START='<!-- END-WORD:START -->'
END='<!-- END-WORD:END -->'


def paragraph(markdown):
    content=re.sub(r'<!--.*?-->','',markdown,flags=re.S).strip()
    blocks=re.split(r'\n\s*\n',content)
    if len(blocks)!=1 or not content:
        raise ValueError('end-word.md must contain one non-empty paragraph')
    return ' '.join(content.split())


def update_content(original,markdown):
    if original.count(START)!=1 or original.count(END)!=1:
        raise ValueError('End-word markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    text=paragraph(markdown)
    picture=section(text)
    return before+START+'\n'+picture+'\n'+END+after


def layout(text,mobile):
    width=480 if mobile else 880
    inset=52 if mobile else 80
    opening,separator,rest=text.partition('，')
    phrases=[opening+separator,rest] if rest else [text]
    rows=[]
    y=54 if mobile else 66
    for index,phrase in enumerate(phrases):
        size=(24 if mobile else 26) if index==0 and rest else (28 if mobile else 36)
        line=''
        for character in phrase:
            if line and chinese_width(line+character,size)>width-inset-16:
                rows.append((line,size,y,index==0 and bool(rest)))
                y+=size*1.55
                line=''
            line+=character
        if line:
            rows.append((line,size,y,index==0 and bool(rest)))
            y+=size*1.55
        if index==0 and rest:
            y+=12
    return width,inset,rows,round(y+35)


def card(text,theme,mobile=False):
    ink,muted=('#f0f6fc','#b1bac4') if theme=='dark' else ('#1f2328','#59636e')
    width,inset,rows,height=layout(text,mobile)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(text,quote=True)}">',
           f'<style>{faces("Chiron End Word","Chiron Italic")}.words{{font-family:{END_WORD}}}.signature{{font-family:{ITALIC}}}</style>',
           f'<text class="words" x="0" y="{106 if mobile else 126}" font-size="{112 if mobile else 154}" fill="{muted}" fill-opacity=".22" aria-hidden="true">“</text>']
    for line,size,y,secondary in rows:
        parts.append(f'<text class="words" x="{inset}" y="{y:.2f}" font-size="{size}" letter-spacing="1" fill="{muted if secondary else ink}">{escape(line)}</text>')
    parts.append(f'<text class="signature" x="{width-16}" y="{height-16}" font-size="{18 if mobile else 16}" text-anchor="end" fill="{muted}">lzsm</text>')
    return ''.join(parts)+'</svg>\n'


def section(text,assets=None):
    paths={}
    for theme in ('light','dark'):
        for mobile in (False,True):
            svg=card(text,theme,mobile)
            path='assets/end-word-'+theme+('-mobile' if mobile else '')+'-'+sha256(svg.encode()).hexdigest()[:12]+'.svg'
            if assets is not None:
                assets[path]=svg
            paths[theme,mobile]=path
    return ('<picture>'
            f'<source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{paths["dark",True]}">'
            f'<source media="(max-width: 600px)" srcset="{paths["light",True]}">'
            f'<source media="(prefers-color-scheme: dark)" srcset="{paths["dark",False]}">'
            f'<img alt="{escape(text,quote=True)}" src="{paths["light",False]}" width="100%"></picture>')


def main():
    readme=ROOT/'README.md'
    original=readme.read_text(encoding='utf-8')
    updated=update_content(original,(ROOT/'end-word.md').read_text(encoding='utf-8'))
    assets={}
    section(paragraph((ROOT/'end-word.md').read_text(encoding='utf-8')),assets)
    (ROOT/'assets').mkdir(exist_ok=True)
    for path,svg in assets.items():
        (ROOT/path).write_text(svg,encoding='utf-8')
    if updated!=original:
        readme.write_text(updated,encoding='utf-8')
    print('End word updated from end-word.md.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        print(f'End word unchanged: {error}',file=sys.stderr)
        sys.exit(1)
