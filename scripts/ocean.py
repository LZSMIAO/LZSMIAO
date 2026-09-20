"""The sea the drift bottle floats on: layered swell, a bottle, and a little sky."""
from math import pi,sin

SEAS={
    'light': dict(sky=('#ffffff','#f2f7fd'),
                  swell=('#eaf2fb','#d3e3f5','#b3cde9'),
                  foam='#ffffff',glass='#57606a',shine='#ffffff',
                  cork='#bf8700',note='#fff8e6',star=None,moon=None),
    'dark': dict(sky=('#0d1117','#111a28'),
                 swell=('#0f1c2c','#14293f','#1b3a58'),
                 foam='#58a6ff',glass='#8b949e',shine='#e6edf3',
                 cork='#9a6700',note='#f0f6fc',star='#c9d1d9',moon='#e6edf3'),
}


def crest(width,length,base,height,phase,step):
    """One periodic swell line, drawn wide enough to scroll by exactly one wavelength."""
    points=[]
    start=-length
    span=width+2*length
    count=max(8,int(span/step))
    for i in range(count+1):
        x=start+span*i/count
        turn=2*pi*x/length+phase
        y=base-height*(sin(turn)+.34*sin(3*turn+1.1)+.16*sin(2*turn-.4))
        points.append(f'{x:.1f},{y:.1f}')
    return 'M'+'L'.join(points)


def ocean(width,height,top,theme,scale=1.0,bottle=True,seed=0):
    """Everything below the waterline, returned as ready-to-drop SVG."""
    sea=SEAS[theme]
    parts=[]
    depth=height-top
    layers=((.20,1.00,26,.62),(.48,1.55,19,.82),(.86,2.30,13,1.00))
    for index,(where,drift,length_divisor,alpha) in enumerate(layers):
        length=width/length_divisor*.55+width/6
        base=top+depth*where*.62+depth*.10
        swell=3.2+3.4*index
        line=crest(width,length,base,swell*scale,seed+index*2.1,7)
        body=f'{line}L{width+length:.1f},{height}L{-length:.1f},{height}Z'
        parts.append(f'<g><animateTransform attributeName="transform" type="translate" '
                     f'values="0,0;{-length:.1f},0" dur="{18+index*9:.0f}s" repeatCount="indefinite"/>'
                     f'<path d="{body}" fill="{sea["swell"][index]}" fill-opacity="{alpha:.2f}"/>'
                     f'<path d="{line}" fill="none" stroke="{sea["foam"]}" stroke-opacity="{.16+.10*index:.2f}" '
                     f'stroke-width="{1.1 if index<2 else 1.4}"/></g>')
        if index==1 and bottle:
            parts.append(floating(width*.725,top+depth*.53,scale*2.0,sea))
    return ''.join(parts)


def floating(x,y,scale,sea):
    """A corked bottle with a note inside, bobbing and tilting on the swell."""
    # One continuous outline: body, shoulder, neck and lip in a single path, so the
    # glass has no internal seams where separate shapes used to meet.
    outline=('M-30,-5.4Q-30,-10 -25.4,-10L8,-10Q17,-10 21.2,-5.6L26.4,-4.6'
             'Q29,-4.2 29,-3.2L29,3.2Q29,4.2 26.4,4.6L21.2,5.6Q17,10 8,10'
             'L-25.4,10Q-30,10 -30,5.4Z')
    glass=(f'<path d="{outline}" fill="{sea["shine"]}" fill-opacity=".07" '
           f'stroke="{sea["glass"]}" stroke-width="1.5" stroke-linejoin="round"/>'
           # The cork sits inside the neck rather than capping it from outside.
           f'<path d="M26.8,-4.4Q33.4,-4 33.4,0Q33.4,4 26.8,4.4Z" fill="{sea["cork"]}"/>'
           f'<path d="M26.8,-4.4Q33.4,-4 33.4,0Q33.4,4 26.8,4.4Z" fill="none" '
           f'stroke="{sea["cork"]}" stroke-width="1.6" stroke-linejoin="round"/>'
           # A rolled note, narrower and dimmer than the glass so it reads as inside.
           f'<g transform="rotate(-4)"><rect x="-20" y="-5.2" width="19" height="10.4" rx="5.2" '
           f'fill="{sea["note"]}" fill-opacity=".62"/>'
           f'<path d="M-16.4,-1.6h11M-16.4,1.8h7.5" stroke="{sea["cork"]}" stroke-opacity=".5" '
           'stroke-width="1.1" stroke-linecap="round"/></g>'
           # Two highlights: a long one along the shoulder, a short one on the base.
           f'<path d="M-25,-6.4Q-16,-8.2 -3,-7.6" fill="none" stroke="{sea["shine"]}" '
           'stroke-opacity=".5" stroke-width="1.7" stroke-linecap="round"/>'
           f'<path d="M-26.6,4.6Q-23,6.2 -19,6.4" fill="none" stroke="{sea["shine"]}" '
           'stroke-opacity=".22" stroke-width="1.3" stroke-linecap="round"/>')
    return (f'<g transform="translate({x:.1f},{y:.1f})">'
            '<animateTransform attributeName="transform" type="translate" additive="sum" '
            'values="0,0;0,-3.4;0,0;0,2.6;0,0" dur="7s" repeatCount="indefinite"/>'
            f'<g transform="scale({scale:.3f})">'
            '<animateTransform attributeName="transform" type="rotate" additive="sum" '
            'values="-7;-1;-7;-12;-7" dur="7s" repeatCount="indefinite"/>'
            f'{glass}</g></g>')


def sky(width,top,theme,seed=0):
    """Gradient, a low moon and a scatter of stars — only the dark sea gets a night."""
    sea=SEAS[theme]
    parts=[]
    if sea['moon']:
        mx,my=width*.885,top*.32
        parts.append(f'<defs><radialGradient id="halo">'
                     f'<stop offset="0" stop-color="{sea["moon"]}" stop-opacity=".16"/>'
                     f'<stop offset=".55" stop-color="{sea["moon"]}" stop-opacity=".05"/>'
                     f'<stop offset="1" stop-color="{sea["moon"]}" stop-opacity="0"/></radialGradient>'
                     f'<mask id="crescent"><circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="#fff"/>'
                     f'<circle cx="{mx+5:.0f}" cy="{my-3.5:.0f}" r="10" fill="#000"/></mask></defs>'
                     f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="34" fill="url(#halo)"/>'
                     f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="{sea["moon"]}" fill-opacity=".40" '
                     'mask="url(#crescent)"/>')
        spots=[(.06,.52,1.0),(.14,.26,.7),(.23,.62,.9),(.35,.20,.6),(.47,.48,.8),
               (.58,.24,.65),(.67,.58,.9),(.78,.32,.7),(.93,.56,.8),(.29,.40,.55)]
        for fx,fy,size in spots:
            parts.append(f'<circle cx="{width*fx:.0f}" cy="{top*fy:.0f}" r="{size:.2f}" '
                         f'fill="{sea["star"]}" fill-opacity="{.20+.30*size:.2f}">'
                         f'<animate attributeName="fill-opacity" values="{.20+.30*size:.2f};'
                         f'{.06+.10*size:.2f};{.20+.30*size:.2f}" dur="{3.5+fx*5:.1f}s" repeatCount="indefinite"/>'
                         '</circle>')
    return ''.join(parts)
