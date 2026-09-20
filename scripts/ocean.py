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
    glass=(f'<rect x="-26" y="-9.5" width="40" height="19" rx="7" fill="{sea["shine"]}" fill-opacity=".07" '
           f'stroke="{sea["glass"]}" stroke-width="1.4"/>'
           f'<path d="M14,-8.4Q23,-7.2 26,-4.2L26,4.2Q23,7.2 14,8.4" fill="{sea["shine"]}" fill-opacity=".07" '
           f'stroke="{sea["glass"]}" stroke-width="1.4" stroke-linejoin="round"/>'
           f'<rect x="25" y="-4.4" width="7" height="8.8" rx="1.2" fill="{sea["glass"]}" fill-opacity=".18" '
           f'stroke="{sea["glass"]}" stroke-width="1.2"/>'
           f'<rect x="31" y="-4.8" width="6" height="9.6" rx="2" fill="{sea["cork"]}"/>'
           f'<rect x="-17" y="-6.6" width="21" height="10" rx="2.4" fill="{sea["note"]}" fill-opacity=".85"/>'
           f'<path d="M-13,-3.8h13M-13,-0.2h9" stroke="{sea["cork"]}" stroke-opacity=".45" stroke-width="1"/>'
           f'<path d="M-22,-5.6Q-14,-7.6 -4,-7" fill="none" stroke="{sea["shine"]}" stroke-opacity=".55" '
           'stroke-width="1.6" stroke-linecap="round"/>')
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
        parts.append(f'<defs><mask id="crescent"><circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="#fff"/>'
                     f'<circle cx="{mx+5:.0f}" cy="{my-3.5:.0f}" r="10" fill="#000"/></mask></defs>'
                     f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="{sea["moon"]}" fill-opacity=".34" '
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
