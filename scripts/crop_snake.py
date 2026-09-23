"""Crop the contribution snake to its grid.

snk pads its viewBox on every side and draws a progress bar under the grid, so
the block sat inset from every other one with a band of empty space above and a
stray green bar below. Cropping to the cells (with a 2px margin for their
stroke) lines its edges up with the column and leaves only the grid itself.
"""
from pathlib import Path
import re
import sys

MARGIN=2
CELL=12


def crop(svg):
    head=re.search(r'<svg\b[^>]*>',svg)
    if not head or 'viewBox=' not in head.group(0):
        raise ValueError('Unexpected snake SVG')
    cells=[(float(x),float(y)) for x,y in re.findall(r'<rect class="c[^"]*" x="(-?[\d.]+)" y="(-?[\d.]+)"',svg)]
    if not cells:
        raise ValueError('No grid cells found')
    left=min(x for x,_ in cells)-MARGIN
    top=min(y for _,y in cells)-MARGIN
    width=max(x for x,_ in cells)+CELL+MARGIN-left
    height=max(y for _,y in cells)+CELL+MARGIN-top
    tag=re.sub(r'viewBox="[^"]*"',f'viewBox="{left:g} {top:g} {width:g} {height:g}"',head.group(0))
    tag=re.sub(r'\bwidth="[\d.]+"',f'width="{width:g}"',tag,count=1)
    tag=re.sub(r'\bheight="[\d.]+"',f'height="{height:g}"',tag,count=1)
    return svg.replace(head.group(0),tag,1)


if __name__=='__main__':
    for name in sys.argv[1:]:
        path=Path(name)
        path.write_text(crop(path.read_text()))
