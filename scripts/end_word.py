"""Publish one quiet closing paragraph from end-word.md, without image assets."""
from html import escape
from pathlib import Path
import re
import sys

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
    text=escape(paragraph(markdown),quote=True)
    return before+START+'\n<p align="center"><em>'+text+'</em></p>\n'+END+after


def main():
    readme=ROOT/'README.md'
    original=readme.read_text(encoding='utf-8')
    updated=update_content(original,(ROOT/'end-word.md').read_text(encoding='utf-8'))
    if updated!=original:
        readme.write_text(updated,encoding='utf-8')
    print('End word updated from end-word.md.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        print(f'End word unchanged: {error}',file=sys.stderr)
        sys.exit(1)
