"""Trim the side margins Platane/snk leaves around the contribution grid.

snk pads its viewBox (-16 wide on the left, ~18 on the right), so at the page's
column width the grid sat inset from every other block. Cropping to the cells and
the progress bar lines its edges up with the column.
"""
from pathlib import Path
import re
import sys


def crop(svg):
    head=re.search(r'<svg\b[^>]*>',svg)
    box=re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"',head.group(0))
    if not head or not box:
        raise ValueError('Unexpected snake SVG')
    _,top,_,height=map(float,box.groups())
    edges=[(float(x),float(x)+12) for x in re.findall(r'<rect class="c[^"]*" x="(-?[\d.]+)"',svg)]
    edges+=[(float(x),float(x)+float(w)) for w,x in re.findall(r'<rect class="u[^"]*" height="[\d.]+" width="([\d.]+)" x="(-?[\d.]+)"',svg)]
    if not edges:
        raise ValueError('No grid cells found')
    left=min(a for a,_ in edges)
    width=max(b for _,b in edges)-left
    tag=re.sub(r'viewBox="[^"]*"',f'viewBox="{left:g} {top:g} {width:g} {height:g}"',head.group(0))
    tag=re.sub(r'\bwidth="[\d.]+"',f'width="{width:g}"',tag,count=1)
    return svg.replace(head.group(0),tag,1)


if __name__=='__main__':
    for name in sys.argv[1:]:
        path=Path(name)
        path.write_text(crop(path.read_text()))
