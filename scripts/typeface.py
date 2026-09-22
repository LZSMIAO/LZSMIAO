"""Chiron Sung HK, embedded: an italic for headings and an upright for figures.

Both are Latin-only subsets (see fonts/build.py), so anything outside printable
ASCII falls through to the next family in the stack, never to a missing glyph.
"""
from base64 import b64encode
from functools import cache
from pathlib import Path

FONTS=Path(__file__).resolve().parent/'fonts'
ITALIC='"Chiron Italic",Georgia,"Times New Roman",serif'
FIGURES='"Chiron Figures",Georgia,"Times New Roman",serif'
FILES={'Chiron Italic':'chiron-italic.woff2','Chiron Figures':'chiron-figures.woff2'}


@cache
def face(family):
    data=b64encode((FONTS/FILES[family]).read_bytes()).decode()
    return f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2")}}'


def faces(*families):
    return ''.join(face(family) for family in families)
