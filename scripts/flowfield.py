"""Particles drifting along a noise field, drawn as travelling dashes on streamlines."""
from hashlib import sha256
from math import cos,pi,sin
import random
import sys
from publish import publish

THEMES={
    'light': dict(bg='#ffffff',ink='#7b7490',glow='#8250df'),
    'dark': dict(bg='#0d1117',ink='#8b86a6',glow='#a371f7'),
}
LANES=6
# Each style is (dash, gap, seconds): the offset animates by exactly one period,
# so a single path reads as a column of particles sliding along the streamline.
# dash, gap, seconds. The gap dominates the period, so it sets how much of each
# streamline is inked at any moment: at 2 on 14 only an eighth of it shows and
# a fully covered field still reads as empty.
STYLES=((2.5,7.5,3.0),(2.5,7.5,3.8),(6,14,5.4))


def field(seed):
    """A smooth angle field built from a few sine terms, so it needs no noise table."""
    rng=random.Random(int(sha256(f'flow/{seed}'.encode()).hexdigest(),16))
    terms=[(rng.uniform(.5,1.4),rng.uniform(.5,1.4),rng.uniform(0,2*pi),rng.uniform(.30,.55))
           for _ in range(3)]
    tilt=rng.uniform(-.25,.25)
    def angle(x,y):
        # Kept under about one radian of swing: a wider field folds streamlines
        # into a hard diagonal crease that reads as a defect rather than a design.
        total=tilt
        for fx,fy,phase,weight in terms:
            total+=weight*sin(fx*2*pi*x+fy*2*pi*y+phase)
        return total
    return angle


def march(angle,x,y,width,height,steps,step):
    points=[]
    for _ in range(steps):
        a=angle(x/width,y/height)
        x+=cos(a)*step
        y+=sin(a)*step
        if not (-34<x<width+34 and -34<y<height+34):
            break
        points.append((x,y))
    return points


def streamline(angle,x,y,width,height,steps,step):
    """Trace both ways from the seed: forward only leaves the upwind edge bare."""
    back=march(angle,x,y,width,height,steps//2,-step)
    return back[::-1]+[(x,y)]+march(angle,x,y,width,height,steps,step)


def sow(angle,width,height,count,rng,step,cols=42,rows=12):
    """Seed wherever the frame is emptiest, then mark what the streamline covered.

    A jittered grid looks even on paper but is not: streamlines funnel onto the
    same trajectories and leave most of the canvas bare. Chasing the emptiest
    cell instead is the difference between two thirds of the frame empty and
    almost none of it.
    """
    covered=[[0]*cols for _ in range(rows)]
    traced=[]
    for _ in range(count):
        low=min(min(row) for row in covered)
        empty=[(r,c) for r in range(rows) for c in range(cols) if covered[r][c]==low]
        r,c=empty[rng.randrange(len(empty))]
        x=width*(c+rng.uniform(.15,.85))/cols
        y=height*(r+rng.uniform(.15,.85))/rows
        points=streamline(angle,x,y,width,height,rng.randint(22,36),step)
        if len(points)<8:
            covered[r][c]+=1
            continue
        for px,py in points:
            covered[min(rows-1,max(0,int(py/height*rows)))][min(cols-1,max(0,int(px/width*cols)))]+=1
        traced.append(points)
    return traced


def card(theme,width=880,height=138,seed='2026',lines=140,mobile=False):
    t=THEMES[theme]
    angle=field(seed)
    rng=random.Random(int(sha256(f'starts/{seed}/{width}'.encode()).hexdigest(),16))
    step=7.0 if not mobile else 5.5
    styles=''.join(
        f'.p{i}{{stroke-dasharray:{dash} {gap};animation:k{i} {secs}s linear infinite}}'
        f'@keyframes k{i}{{to{{stroke-dashoffset:{-(dash+gap)}}}}}'
        for i,(dash,gap,secs) in enumerate(STYLES))
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="flow-title flow-desc">',
           '<title id="flow-title">Flow field</title>',
           f'<desc id="flow-desc">{lines} streamlines traced through a smooth angle field. '
           'Each carries a column of dashes that slides along it, so the field reads as '
           'drifting particles.</desc>',
           '<style>path{fill:none;stroke-linecap:round}'+styles
           +''.join(f'.d{i}{{animation-delay:{-6*i/LANES:.2f}s}}' for i in range(LANES))
           +'</style>',
           f'<clipPath id="flow-clip"><rect width="{width}" height="{height}" rx="12"/></clipPath>',
           f'<rect width="{width}" height="{height}" rx="12" fill="{t["bg"]}"/>',
           '<g clip-path="url(#flow-clip)">']
    for i,points in enumerate(sow(angle,width,height,lines,rng,step)):
        d='M'+'L'.join(f'{px:.0f},{py:.0f}' for px,py in points)
        style=2 if rng.random()<.18 else rng.randrange(2)
        colour=t['glow'] if rng.random()<.28 else t['ink']
        parts.append(f'<path class="p{style} d{i%LANES}" d="{d}" stroke="{colour}" '
                     f'stroke-opacity="{rng.uniform(.38,.88):.2f}" '
                     f'stroke-width="{rng.uniform(1.3,2.3):.1f}"/>')
    parts += ['</g>','</svg>\n']
    return ''.join(parts)


def main():
    publish({'flow-'+theme+('-mobile' if mobile else ''):card(theme,480,92,lines=115,mobile=True) if mobile
             else card(theme,880,138)
             for mobile in (False,True) for theme in ('light','dark')})
    print('Flow field redrawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Flow field unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
