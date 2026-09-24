"""Fit the contribution snake to the column.

snk pads its viewBox on every side, so the grid sat inset from every other
block, and it hangs a 12px progress bar 34px below the grid. This crops to the
cells (with a 2px margin for their stroke) and keeps the bar, restyled to the
page: 4px tall with round ends, 10px under the grid, stretched to the grid's
exact width. The bar segments grow by a CSS transform, so they are wrapped in a
group that carries the placement, and their own animation stays untouched.
"""
from pathlib import Path
import re
import sys

MARGIN=2
CELL=12
GAP=10
BAR=4


def crop(svg):
    head=re.search(r'<svg\b[^>]*>',svg)
    if not head or 'viewBox=' not in head.group(0):
        raise ValueError('Unexpected snake SVG')
    cells=[(float(x),float(y)) for x,y in re.findall(r'<rect class="c[^"]*" x="(-?[\d.]+)" y="(-?[\d.]+)"',svg)]
    if not cells:
        raise ValueError('No grid cells found')
    left=min(x for x,_ in cells)
    right=max(x for x,_ in cells)+CELL
    top=min(y for _,y in cells)
    bottom=max(y for _,y in cells)+CELL
    edge=bottom
    if 'class="bar-row"' not in svg:
        segments=re.findall(r'<rect class="u[^"]*"[^>]*/>',svg)
        if segments:
            spans=[(float(re.search(r'\bx="(-?[\d.]+)"',s).group(1)),float(re.search(r'\bwidth="([\d.]+)"',s).group(1))) for s in segments]
            start=min(x for x,_ in spans)
            end=max(x+w for x,w in spans)
            scale=(right-left)/(end-start)
            restyled=[re.sub(r'\by="[^"]*"','y="0"',re.sub(r'\bheight="[^"]*"',f'height="{BAR}" rx="{BAR/2:g}"',s)) for s in segments]
            group=(f'<g class="bar-row" transform="translate({left-start*scale:g} {bottom+GAP:g}) scale({scale:.5f} 1)">'
                   +''.join(restyled)+'</g>')
            first=svg.index(segments[0])
            last=svg.index(segments[-1])+len(segments[-1])
            svg=svg[:first]+group+svg[last:]
    if 'class="bar-row"' in svg:
        edge=bottom+GAP+BAR
    head=re.search(r'<svg\b[^>]*>',svg)
    width=right+MARGIN-(left-MARGIN)
    height=edge+MARGIN-(top-MARGIN)
    tag=re.sub(r'viewBox="[^"]*"',f'viewBox="{left-MARGIN:g} {top-MARGIN:g} {width:g} {height:g}"',head.group(0))
    tag=re.sub(r'\bwidth="[\d.]+"',f'width="{width:g}"',tag,count=1)
    tag=re.sub(r'\bheight="[\d.]+"',f'height="{height:g}"',tag,count=1)
    return svg.replace(head.group(0),tag,1)


if __name__=='__main__':
    for name in sys.argv[1:]:
        path=Path(name)
        path.write_text(crop(path.read_text()))
