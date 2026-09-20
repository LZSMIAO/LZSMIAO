"""A contour header seeded by the calendar day, so it redraws itself each morning."""
from datetime import datetime
from hashlib import sha256
from html import escape
from math import exp,pi,sin
import random
import sys
from zoneinfo import ZoneInfo
from publish import publish

THEMES={
    'light': dict(bg='#ffffff',line='#59636e',accent='#2da44e',label='#8c959f'),
    'dark': dict(bg='#0d1117',line='#b1bac4',accent='#3fb950',label='#6e7681'),
}


def shape(day):
    """Everything random about a day, decided once so every renderer agrees."""
    rng=random.Random(int(sha256(f'LZSMIAO/{day}'.encode()).hexdigest(),16))
    count=rng.randint(19,25)
    # Peaks stay in the middle two thirds: an edge peak reads as a half-cropped accident.
    peaks=[(rng.uniform(.24,.76),rng.uniform(-.05,1.05),rng.uniform(.30,.50),
            rng.uniform(.07,.16),rng.uniform(.24,.52)) for _ in range(rng.randint(2,4))]
    return dict(count=count,peaks=peaks,accent=rng.randrange(count),
                ripple=(rng.uniform(1.4,3.6),rng.uniform(0,2*pi),rng.uniform(.012,.030)))


def card(day,theme,mobile=False):
    t=THEMES[theme]
    s=shape(day)
    width,height=(480,150) if mobile else (880,200)
    top,bottom,pad=26,height-34,20 if mobile else 26
    span=bottom-top
    freq,phase,depth=s['ripple']
    def height_at(x,y):
        # Peaks are stored as fractions so desktop and mobile share one silhouette.
        total=depth*sin(freq*2*pi*x+phase)
        for cx,cy,amp,sx,sy in s['peaks']:
            total+=amp*exp(-(((x-cx)/sx)**2+((y-cy)/sy)**2))
        return total*span
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="art-title art-desc">',
           f'<title id="art-title">Generated header for {day}</title>',
           '<desc id="art-desc">{}</desc>'.format(escape(
               '{} contour lines shaped by {} peaks, drawn from the date {}.'.format(s['count'],len(s['peaks']),day))),
           '<style>text{font-family:ui-monospace,"SFMono-Regular",Consolas,monospace;font-variant-numeric:tabular-nums}</style>',
           f'<clipPath id="art-clip"><rect width="{width}" height="{height}" rx="12"/></clipPath>',
           f'<rect width="{width}" height="{height}" rx="12" fill="{t["bg"]}"/>',
           f'<g clip-path="url(#art-clip)" fill="{t["bg"]}" stroke-width="1.3">']
    samples=44 if mobile else 68
    for i in range(s['count']):
        fraction=i/(s['count']-1)
        baseline=top+span*fraction
        points=[]
        for j in range(samples+1):
            fx=-.02+1.04*j/samples
            # Never let a crest breach the top edge: a clipped line reads as a mistake.
            points.append((fx*width,max(top-2,baseline-height_at(fx,fraction))))
        # The closing edges sit outside the viewBox, so only the contour itself shows.
        path='M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in points)+f'L{width*1.02:.1f},{height+24}L{-width*.02:.1f},{height+24}Z'
        chosen=i==s['accent']
        # The single coloured thread keeps a floor so the depth ramp cannot bury it.
        opacity=max(.75,.30+.55*fraction) if chosen else .30+.55*fraction
        parts.append(f'<path d="{path}" stroke="{t["accent"] if chosen else t["line"]}" stroke-opacity="{opacity:.2f}"/>')
    parts.append('</g>')
    parts.append(f'<text x="{width-pad}" y="{height-14}" font-size="12" fill="{t["label"]}" text-anchor="end">{day}</text>')
    return ''.join(parts)+'</svg>\n'


def main():
    day=str(datetime.now(ZoneInfo('Asia/Hong_Kong')).date())
    publish({f'art-{theme}'+('-mobile' if mobile else ''):card(day,theme,mobile)
             for mobile in (False,True) for theme in ('light','dark')})
    print(f'Header redrawn for {day}.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Header unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
