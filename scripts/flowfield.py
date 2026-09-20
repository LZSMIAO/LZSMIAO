"""Particles drifting along a noise field, drawn as travelling dashes on streamlines."""
from hashlib import sha256
from math import cos,pi,sin
import random
import sys
from publish import publish

THEMES={
    'light': dict(bg='#ffffff',ink='#6e7781',glow='#0969da'),
    'dark': dict(bg='#0d1117',ink='#8b949e',glow='#58a6ff'),
}
LANES=6
# Each style is (dash, gap, seconds): the offset animates by exactly one period,
# so a single path reads as a column of particles sliding along the streamline.
STYLES=((2,14,3.4),(2,14,4.2),(5,27,6.0))


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


def streamline(angle,x,y,width,height,steps,step):
    points=[(x,y)]
    for _ in range(steps):
        a=angle(x/width,y/height)
        x+=cos(a)*step
        y+=sin(a)*step
        if not (-30<x<width+30 and -30<y<height+30):
            break
        points.append((x,y))
    return points


def card(theme,width=880,height=300,seed='2026',lines=200,mobile=False):
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
    columns=19
    rows=max(1,lines//columns)
    drawn=0
    for i in range(lines):
        col,row=i%columns,i//columns
        # Start slightly outside so streamlines enter from beyond the frame.
        x=width*(col+rng.uniform(.05,.95))/columns*1.12-width*.06
        y=height*(row+rng.uniform(.05,.95))/rows*1.12-height*.06
        points=streamline(angle,x,y,width,height,rng.randint(30,52),step)
        if len(points)<10:
            continue
        drawn+=1
        d='M'+'L'.join(f'{px:.0f},{py:.0f}' for px,py in points)
        style=2 if rng.random()<.18 else rng.randrange(2)
        colour=t['glow'] if rng.random()<.28 else t['ink']
        parts.append(f'<path class="p{style} d{i%LANES}" d="{d}" stroke="{colour}" '
                     f'stroke-opacity="{rng.uniform(.38,.88):.2f}" '
                     f'stroke-width="{rng.uniform(1.3,2.3):.1f}"/>')
    parts += ['</g>','</svg>\n']
    return ''.join(parts)


def main():
    publish({'flow-'+theme+('-mobile' if mobile else ''):card(theme,480,200,lines=130,mobile=True) if mobile
             else card(theme,880,300)
             for mobile in (False,True) for theme in ('light','dark')})
    print('Flow field redrawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Flow field unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
