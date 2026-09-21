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
    """A corked bottle with a rolled note, bobbing and tilting on the swell."""
    # Silhouette in one path: rounded base, long cubic shoulder, neck, flared lip.
    body=('M-36,-6.4Q-36,-11 -31,-11L5,-11C13.5,-11 18.5,-8.7 23,-5.1'
          'L27,-4.3L32.4,-4.3Q35.4,-4.3 35.4,-3.1L35.4,3.1'
          'Q35.4,4.3 32.4,4.3L27,4.3L23,5.1C18.5,8.7 13.5,11 5,11'
          'L-31,11Q-36,11 -36,6.4Z')
    parts=[f'<defs><linearGradient id="pane" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{sea["shine"]}" stop-opacity=".17"/>'
           f'<stop offset=".45" stop-color="{sea["shine"]}" stop-opacity=".06"/>'
           f'<stop offset="1" stop-color="{sea["shine"]}" stop-opacity=".02"/>'
           '</linearGradient></defs>',
           f'<path d="{body}" fill="url(#pane)" stroke="{sea["glass"]}" stroke-opacity=".85" '
           'stroke-width="1.1" stroke-linejoin="round"/>',
           # One shape, uniform bore width, standing proud of the lip. A stepped
           # head and a seam both read as two separate objects at display size.
           f'<rect x="27" y="-3" width="12.4" height="6" rx="1.4" fill="{sea["cork"]}"/>',
           f'<path d="M27,1.2h12.4v1.4Q39.4,3 38,3L27,3Z" fill="#000000" fill-opacity=".18"/>',
           f'<path d="M28.4,-2.1Q33,-2.4 37.6,-1.9" fill="none" stroke="{sea["shine"]}" '
           'stroke-opacity=".28" stroke-width=".9" stroke-linecap="round"/>',
           f'<path d="M35.4,-3L35.4,3" stroke="#000000" stroke-opacity=".22" stroke-width=".8"/>',
           # A sheet of paper with a curled edge and three lines of writing. Rolled
           # into a tube it read as a battery once the spiral shrank to a few pixels.
           '<g transform="rotate(-7)">',
           f'<path d="M-24,-6.2L-6.2,-6.2Q-4.4,-6.2 -4.4,-4.6L-4.4,5Q-4.4,6.4 -6.2,6.4'
           f'L-22.2,6.4Q-24,6.4 -24,4.8Z" fill="{sea["note"]}" fill-opacity=".92"/>',
           f'<path d="M-24,4.8Q-20.4,2.4 -16.6,4.6Q-13,6.6 -9.4,4.8L-9.4,6.4L-22.2,6.4Q-24,6.4 -24,4.8Z" '
           f'fill="{sea["cork"]}" fill-opacity=".2"/>',
           f'<path d="M-21,-3.2h13.2M-21,-0.4h10.4M-21,2.4h12" stroke="{sea["cork"]}" '
           'stroke-opacity=".55" stroke-width="1.15" stroke-linecap="round"/>',
           '</g>',
           # Two speculars: a long one riding the shoulder, a short catch on the base.
           f'<path d="M-29.5,-7.4Q-16,-9.4 2,-8.5" fill="none" stroke="{sea["shine"]}" '
           'stroke-opacity=".62" stroke-width="1.9" stroke-linecap="round"/>',
           f'<path d="M-32,5.4Q-27.5,7.6 -22.5,8" fill="none" stroke="{sea["shine"]}" '
           'stroke-opacity=".2" stroke-width="1.4" stroke-linecap="round"/>']
    return (f'<g transform="translate({x:.1f},{y:.1f})">'
            '<animateTransform attributeName="transform" type="translate" additive="sum" '
            'values="0,0;0,-3.4;0,0;0,2.6;0,0" dur="7s" repeatCount="indefinite"/>'
            f'<g transform="scale({scale:.3f})">'
            '<animateTransform attributeName="transform" type="rotate" additive="sum" '
            'values="-7;-1;-7;-12;-7" dur="7s" repeatCount="indefinite"/>'
            +''.join(parts)+'</g></g>')


def sky(width,top,theme,seed=0):
    """Gradient, a low moon and a scatter of stars — only the dark sea gets a night."""
    sea=SEAS[theme]
    parts=[]
    if sea['moon']:
        mx,my=width*.885,top*.32
        # The lit crescent sits down-left of the disc centre, so the halo is centred
        # there too; a glow centred on the shadowed half reads as misaligned.
        gx,gy=mx-2.6,my+1.4
        stops=((0,.22),(.16,.17),(.34,.10),(.55,.045),(.78,.014),(1,0))
        parts.append('<defs>'
                     f'<radialGradient id="halo" gradientUnits="userSpaceOnUse" '
                     f'cx="{gx:.1f}" cy="{gy:.1f}" r="42">'
                     +''.join(f'<stop offset="{o}" stop-color="{sea["moon"]}" stop-opacity="{a}"/>'
                              for o,a in stops)+'</radialGradient>'
                     f'<radialGradient id="core" gradientUnits="userSpaceOnUse" '
                     f'cx="{gx:.1f}" cy="{gy:.1f}" r="16">'
                     f'<stop offset="0" stop-color="{sea["moon"]}" stop-opacity=".20"/>'
                     f'<stop offset=".6" stop-color="{sea["moon"]}" stop-opacity=".07"/>'
                     f'<stop offset="1" stop-color="{sea["moon"]}" stop-opacity="0"/></radialGradient>'
                     f'<mask id="crescent"><circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="#fff"/>'
                     f'<circle cx="{mx+5:.0f}" cy="{my-3.5:.0f}" r="10" fill="#000"/></mask></defs>'
                     f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="42" fill="url(#halo)"/>'
                     f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="16" fill="url(#core)"/>'
                     f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="11" fill="{sea["moon"]}" fill-opacity=".46" '
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
