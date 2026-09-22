"""The sea the drift bottle floats on, drawn in the same line work as the header.

The header is contour lines on a bare background and the flow field is dashes on
streamlines; a filled gradient sea under a glowing moon read as a picture book
pasted between them. So the sea is a stack of swell lines, and the bottle is an
outline riding one of them.
"""
from math import atan,cos,degrees,pi,sin

SEAS={
    'light': dict(bg='#ffffff',line='#59636e',accent='#0969da'),
    'dark': dict(bg='#0d1117',line='#b1bac4',accent='#58a6ff'),
}
LINES=9
# The bottle rides this line, counted down from the horizon.
RIDE=3
SAMPLES=32


def swell(turn):
    return sin(turn)+.34*sin(3*turn+1.1)+.16*sin(2*turn-.4)


def rise(turn):
    """d(swell)/d(turn), for the bottle's tilt."""
    return cos(turn)+1.02*cos(3*turn+1.1)+.32*cos(2*turn-.4)


def crest(width,length,base,height,phase,step):
    """One periodic swell line, drawn wide enough to scroll by exactly one wavelength."""
    points=[]
    start=-length
    span=width+2*length
    count=max(8,int(span/step))
    for i in range(count+1):
        x=start+span*i/count
        y=base-height*swell(2*pi*x/length+phase)
        points.append(f'{x:.1f},{y:.1f}')
    return 'M'+'L'.join(points)


def rows(width,height,top,scale):
    """Perspective: lines bunch up at the horizon and open out toward the viewer."""
    depth=height-top
    for i in range(LINES):
        near=i/(LINES-1)
        yield dict(base=top+6+(depth-14)*near**1.45,
                   length=(width/9+width/5*near)*scale,
                   height=(1.2+3.6*near)*scale,
                   phase=i*1.7,
                   seconds=round(34-16*near),
                   opacity=.16+.46*near)


def ocean(width,height,top,theme,scale=1.0,bottle=True,seed=0):
    """Everything below the horizon, returned as ready-to-drop SVG."""
    sea=SEAS[theme]
    parts=[]
    for index,row in enumerate(rows(width,height,top,scale)):
        line=crest(width,row['length'],row['base'],row['height'],seed+row['phase'],6)
        ride=bottle and index==RIDE
        colour=sea['accent'] if ride else sea['line']
        opacity=max(.7,row['opacity']) if ride else row['opacity']
        if ride:
            # Drawn before its own line, so the waterline cuts across the hull.
            parts.append(floating(width*.72,row,seed,scale*1.15,sea))
        parts.append(f'<g><animateTransform attributeName="transform" type="translate" '
                     f'values="0,0;{-row["length"]:.1f},0" dur="{row["seconds"]}s" repeatCount="indefinite"/>'
                     f'<path d="{line}" fill="none" stroke="{colour}" stroke-opacity="{opacity:.2f}" '
                     'stroke-width="1.3"/></g>')
    return ''.join(parts)


def floating(x,row,seed,scale,sea):
    """An outlined bottle that rides its swell line instead of bobbing on its own.

    The line scrolls left by one wavelength per cycle, so the water under a fixed
    x repeats with the same period; sampling it gives the bottle's lift and tilt.
    """
    length,height,phase=row['length'],row['height'],seed+row['phase']
    lift=[]
    tilt=[]
    for k in range(SAMPLES+1):
        turn=2*pi*(x+length*k/SAMPLES)/length+phase
        lift.append(f'{x:.1f},{row["base"]-height*swell(turn)-4.2*scale:.1f}')
        # Damped: a bottle this long spans part of a wave and never follows it fully.
        tilt.append(f'{-.55*degrees(atan(height*rise(turn)*2*pi/length)):.1f}')
    body=('M-36,-6.4Q-36,-11 -31,-11L5,-11C13.5,-11 18.5,-8.7 23,-5.1'
          'L27,-4.3L32.4,-4.3Q35.4,-4.3 35.4,-3.1L35.4,3.1'
          'Q35.4,4.3 32.4,4.3L27,4.3L23,5.1C18.5,8.7 13.5,11 5,11'
          'L-31,11Q-36,11 -36,6.4Z')
    stroke=f'{1.3/scale:.2f}'
    drawing=(f'<path d="{body}" fill="{sea["bg"]}" stroke="{sea["accent"]}" stroke-width="{stroke}" '
             'stroke-linejoin="round"/>'
             f'<rect x="35.4" y="-2.8" width="5.4" height="5.6" rx="1.2" fill="{sea["accent"]}"/>'
             f'<g transform="rotate(-6)"><rect x="-24" y="-5.6" width="18" height="11.6" rx="1.4" '
             f'fill="none" stroke="{sea["line"]}" stroke-opacity=".7" stroke-width="{stroke}"/>'
             f'<path d="M-20.6,-2h11M-20.6,1.6h8" stroke="{sea["line"]}" stroke-opacity=".7" '
             f'stroke-width="{stroke}" stroke-linecap="round"/></g>'
             f'<path d="M-30,-7.2Q-16,-8.8 0,-8" fill="none" stroke="{sea["accent"]}" '
             f'stroke-opacity=".45" stroke-width="{stroke}" stroke-linecap="round"/>')
    seconds=f'{row["seconds"]}s'
    return (f'<g transform="translate({lift[0]})">'
            f'<animateTransform attributeName="transform" type="translate" values="{";".join(lift)}" '
            f'dur="{seconds}" repeatCount="indefinite"/>'
            f'<g transform="rotate({tilt[0]})">'
            f'<animateTransform attributeName="transform" type="rotate" values="{";".join(tilt)}" '
            f'dur="{seconds}" repeatCount="indefinite"/>'
            f'<g transform="scale({scale:.3f})">{drawing}</g></g></g>')
