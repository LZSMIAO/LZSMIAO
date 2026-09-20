"""A prism that actually refracts: Snell's law per wavelength, solved before it is drawn."""
from math import atan2,cos,degrees,radians,sin,sqrt
import sys
from publish import publish

# Cauchy coefficients for SF11 dense flint: picked because it disperses hard enough to see.
CAUCHY_A,CAUCHY_B=1.7847,0.01280
SAMPLES=104


def index(nm):
    """Refractive index at one wavelength; Cauchy wants micrometres."""
    micron=nm/1000
    return CAUCHY_A+CAUCHY_B/(micron*micron)


def spectrum(nm):
    """Approximate sRGB for a visible wavelength, dimmed towards both ends."""
    if nm<440: r,g,b=-(nm-440)/60,0.0,1.0
    elif nm<490: r,g,b=0.0,(nm-440)/50,1.0
    elif nm<510: r,g,b=0.0,1.0,-(nm-510)/20
    elif nm<580: r,g,b=(nm-510)/70,1.0,0.0
    elif nm<645: r,g,b=1.0,-(nm-645)/65,0.0
    else: r,g,b=1.0,0.0,0.0
    if nm<420: fade=.3+.7*(nm-380)/40
    elif nm>700: fade=.3+.7*(780-nm)/80
    else: fade=1.0
    return tuple(min(255,max(0,round(255*(v*fade)**.8))) for v in (r,g,b))


def unit(v):
    length=sqrt(v[0]*v[0]+v[1]*v[1])
    return (v[0]/length,v[1]/length)


def refract(direction,normal,eta):
    """Vector Snell; returns None when the ray is totally internally reflected."""
    cosine=-(normal[0]*direction[0]+normal[1]*direction[1])
    if cosine<0:
        normal=(-normal[0],-normal[1])
        cosine=-cosine
    k=1-eta*eta*(1-cosine*cosine)
    if k<0:
        return None
    scale=eta*cosine-sqrt(k)
    return unit((eta*direction[0]+scale*normal[0],eta*direction[1]+scale*normal[1]))


def hit(origin,direction,a,b):
    """Where a ray meets the segment ab, or None."""
    ex,ey=b[0]-a[0],b[1]-a[1]
    denominator=direction[0]*ey-direction[1]*ex
    if abs(denominator)<1e-9:
        return None
    ox,oy=a[0]-origin[0],a[1]-origin[1]
    t=(ox*ey-oy*ex)/denominator
    u=(ox*direction[1]-oy*direction[0])/denominator
    if t<1e-6 or not 0<=u<=1:
        return None
    return (origin[0]+direction[0]*t,origin[1]+direction[1]*t)


def normal_of(a,b):
    edge=unit((b[0]-a[0],b[1]-a[1]))
    return (edge[1],-edge[0])


def trace(entry,direction,nm,faces,width):
    """Enter the first face, leave through the second, then run off the canvas."""
    front,back=faces
    inside=refract(direction,normal_of(*front),1/index(nm))
    if inside is None:
        return None
    exit_point=hit(entry,inside,*back)
    if exit_point is None:
        return None
    outward=refract(inside,normal_of(*back),index(nm))
    if outward is None:
        return None
    distance=(width*1.4-exit_point[0])/outward[0] if outward[0]>1e-6 else width
    end=(exit_point[0]+outward[0]*distance,exit_point[1]+outward[1]*distance)
    return exit_point,end



def solve(incidence,side=1.0):
    """Trace every wavelength through a canonical apex-up prism centred on the origin."""
    tall=side*.86602
    apex=(0.0,-tall*2/3)
    left=(-side/2,tall/3)
    right=(side/2,tall/3)
    entry=(apex[0]+.46*(left[0]-apex[0]),apex[1]+.46*(left[1]-apex[1]))
    heading=unit((cos(radians(incidence)),sin(radians(incidence))))
    front,back=(apex,left),(apex,right)
    rays=[]
    for i in range(SAMPLES):
        nm=400+300*i/(SAMPLES-1)
        inside=refract(heading,normal_of(*front),1/index(nm))
        if inside is None:
            return None
        leaving=hit(entry,inside,*back)
        if leaving is None:
            return None
        outward=refract(inside,normal_of(*back),index(nm))
        if outward is None:
            return None
        rays.append((nm,leaving,outward))
    return dict(corners=(apex,left,right),entry=entry,heading=heading,rays=rays)


def spin(point,angle):
    c,s=cos(angle),sin(angle)
    return (point[0]*c-point[1]*s,point[0]*s+point[1]*c)


def best_incidence():
    """The widest fan the glass allows without total internal reflection."""
    widest=None
    for tenths in range(-750,760):
        solved=solve(tenths/10)
        if not solved:
            continue
        angles=[atan2(o[1],o[0]) for _,_,o in solved['rays']]
        spread=max(angles)-min(angles)
        if widest is None or spread>widest[1]:
            widest=(tenths/10,spread)
    return widest


INCIDENCE=-29.7


def card(width=880,height=300,incidence=INCIDENCE,tilt=6.0,flip=True):
    solved=solve(incidence)
    if not solved:
        raise ValueError('That incidence angle is totally internally reflected')
    angles=[atan2(out[1],out[0]) for _,_,out in solved['rays']]
    # Spin the solved optics until the fan lies flat, then tip it slightly downhill.
    turn=-(sum(angles)/len(angles))+radians(tilt)
    scale=height*.50
    origin=(width*.235,height*.44)
    sign=-1 if flip else 1
    def place(point):
        x,y=spin(point,turn)
        return (origin[0]+x*scale,origin[1]+sign*y*scale)
    def steer(direction):
        x,y=spin(direction,turn)
        return unit((x,sign*y))
    entry=place(solved['entry'])
    heading=steer(solved['heading'])
    source=(entry[0]-heading[0]*height*1.6,entry[1]-heading[1]*height*1.6)
    beams=[]
    for nm,leaving,outward in solved['rays']:
        start=place(leaving)
        way=steer(outward)
        reach=(width*1.02-start[0])/way[0] if way[0]>1e-6 else 0
        beams.append(((start,(start[0]+way[0]*reach,start[1]+way[1]*reach)),'#%02x%02x%02x'%spectrum(nm)))
    corners=' '.join(f'{x:.1f},{y:.1f}' for x,y in map(place,solved['corners']))
    spread=degrees(max(angles)-min(angles))
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="prism-title prism-desc">',
           '<title id="prism-title">Prism</title>',
           f'<desc id="prism-desc">White light entering a glass prism and leaving as a spectrum '
           f'fanned {spread:.1f} degrees wide, refracted by Snell’s law at {SAMPLES} wavelengths '
           f'from 400 to 700 nanometres.</desc>',
           '<defs>',
           '<filter id="bloom" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>',
           '<filter id="haze" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="2.4"/></filter>',
           f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="{origin[0]:.0f}" x2="{width}" y1="0" y2="0">'
           '<stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#fff" stop-opacity=".6"/>'
           '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
           '<mask id="tail"><rect width="100%" height="100%" fill="url(#fade)"/></mask>',
           '<linearGradient id="glass" x1="0" y1="0" x2=".7" y2="1">'
           '<stop offset="0" stop-color="#ffffff" stop-opacity=".13"/>'
           '<stop offset="1" stop-color="#ffffff" stop-opacity=".02"/></linearGradient>',
           '</defs>',
           f'<rect width="{width}" height="{height}" rx="12" fill="#08090b"/>',
           '<g mask="url(#tail)">']
    for blur,opacity,thickness in (('bloom',.26,5.0),('haze',.40,2.6),(None,.62,1.5)):
        filtered=f' filter="url(#{blur})"' if blur else ''
        parts.append(f'<g style="mix-blend-mode:screen" stroke-linecap="round"{filtered}>')
        parts += [f'<path d="M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}" stroke="{colour}" '
                  f'stroke-width="{thickness}" stroke-opacity="{opacity}"/>' for (a,b),colour in beams]
        parts.append('</g>')
    beam=(f'<path d="M{source[0]:.1f},{source[1]:.1f}L{entry[0]:.1f},{entry[1]:.1f}" '
          'stroke="#ffffff" stroke-linecap="round"')
    parts += ['</g>',
              f'<g style="mix-blend-mode:screen">{beam} stroke-width="6" stroke-opacity=".16" filter="url(#bloom)"/>'
              f'{beam} stroke-width="1.6" stroke-opacity=".92"/></g>',
              f'<polygon points="{corners}" fill="url(#glass)" stroke="#ffffff" stroke-opacity=".30" stroke-width="1.1"/>']
    return ''.join(parts)+'</svg>\n'


# The last few degrees before total internal reflection, where dispersion runs away.
LOW,HIGH=-36.0,-29.7


def dispersion(incidence):
    solved=solve(incidence)
    if not solved:
        return None
    angles=[atan2(out[1],out[0]) for _,_,out in solved['rays']]
    return max(angles)-min(angles)


def keyframes(count=7):
    """Incidence angles spaced by equal dispersion, because dispersion explodes near TIR."""
    scale=[(a/10,dispersion(a/10)) for a in range(int(LOW*10),int(HIGH*10)+1)]
    scale=[(a,d) for a,d in scale if d is not None]
    lo,hi=scale[0][1],scale[-1][1]
    picks=[]
    for i in range(count):
        target=lo+(hi-lo)*i/(count-1)
        picks.append(min(scale,key=lambda row:abs(row[1]-target))[0])
    return picks


def animated(width=880,height=300,beams=48,seconds=16,flip=True):
    """The same optics, re-solved per keyframe and handed to SMIL as scalars."""
    middle=solve((LOW+HIGH)/2)['rays']
    angles=[atan2(o[1],o[0]) for _,_,o in middle]
    turn=-(sum(angles)/len(angles))+radians(4.0)
    scale=height*.50
    origin=(width*.235,height*.44)
    sign=-1 if flip else 1
    def place(point):
        x,y=spin(point,turn)
        return (origin[0]+x*scale,origin[1]+sign*y*scale)
    def steer(direction):
        x,y=spin(direction,turn)
        return unit((x,sign*y))
    edge=width*1.02
    stops=keyframes()
    stops=stops+stops[-2:0:-1]
    frames=[]
    for incidence in stops:
        solved=solve(incidence)
        picked=[solved['rays'][round(i*(SAMPLES-1)/(beams-1))] for i in range(beams)]
        entry=place(solved['entry'])
        heading=steer(solved['heading'])
        rays=[]
        for nm,leaving,outward in picked:
            start=place(leaving)
            way=steer(outward)
            rays.append((start,start[1]+way[1]*(edge-start[0])/way[0]))
        frames.append(dict(entry=entry,heading=heading,rays=rays,
                           corners=[place(c) for c in solved['corners']]))
    def track(values,name):
        joined=';'.join(f'{v:.1f}' for v in values)
        return (f'<animate attributeName="{name}" values="{joined}" dur="{seconds}s" '
                'repeatCount="indefinite"/>')
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="prism-title prism-desc">',
           '<title id="prism-title">Prism</title>',
           f'<desc id="prism-desc">A beam sweeping across a glass prism. Every frame is solved '
           f'with Snell’s law at {beams} wavelengths from 400 to 700 nanometres, so the spectrum '
           f'widens from {degrees(dispersion(LOW)):.1f} to {degrees(dispersion(HIGH)):.1f} degrees as '
           'the light approaches total internal reflection.</desc>',
           '<defs>',
           '<filter id="bloom" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>',
           f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="{origin[0]:.0f}" x2="{width}" y1="0" y2="0">'
           '<stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#fff" stop-opacity=".6"/>'
           '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
           '<mask id="tail"><rect width="100%" height="100%" fill="url(#fade)"/></mask>',
           '<linearGradient id="glass" x1="0" y1="0" x2=".7" y2="1">'
           '<stop offset="0" stop-color="#ffffff" stop-opacity=".13"/>'
           '<stop offset="1" stop-color="#ffffff" stop-opacity=".02"/></linearGradient>',
           '</defs>',
           f'<rect width="{width}" height="{height}" rx="12" fill="#08090b"/>',
           '<g mask="url(#tail)">']
    for blur,opacity,thickness in (('bloom',.30,6.0),(None,.62,2.4)):
        filtered=f' filter="url(#{blur})"' if blur else ''
        parts.append(f'<g style="mix-blend-mode:screen" stroke-linecap="round"{filtered}>')
        for index_ in range(beams):
            nm=400+300*round(index_*(SAMPLES-1)/(beams-1))/(SAMPLES-1)
            colour='#%02x%02x%02x'%spectrum(nm)
            parts.append(f'<line x2="{edge:.0f}" stroke="{colour}" stroke-width="{thickness}" '
                         f'stroke-opacity="{opacity}">'
                         +track([f['rays'][index_][0][0] for f in frames],'x1')
                         +track([f['rays'][index_][0][1] for f in frames],'y1')
                         +track([f['rays'][index_][1] for f in frames],'y2')
                         +'</line>')
        parts.append('</g>')
    parts.append('</g>')
    reach=height*1.6
    parts.append('<g style="mix-blend-mode:screen" stroke="#ffffff" stroke-linecap="round">')
    for thickness,alpha,filtered in ((6,'.16',' filter="url(#bloom)"'),(1.6,'.92','')):
        parts.append(f'<line stroke-width="{thickness}" stroke-opacity="{alpha}"{filtered}>'
                     +track([f['entry'][0]-f['heading'][0]*reach for f in frames],'x1')
                     +track([f['entry'][1]-f['heading'][1]*reach for f in frames],'y1')
                     +track([f['entry'][0] for f in frames],'x2')
                     +track([f['entry'][1] for f in frames],'y2')
                     +'</line>')
    corners=' '.join(f'{x:.1f},{y:.1f}' for x,y in frames[0]['corners'])
    parts += ['</g>',f'<polygon points="{corners}" fill="url(#glass)" stroke="#ffffff" '
              'stroke-opacity=".30" stroke-width="1.1"/>']
    return ''.join(parts)+'</svg>\n'


def main():
    """The optics never change, so this only needs running when the drawing does."""
    publish({'prism':animated(880,300),'prism-mobile':animated(480,200,beams=36)})
    print('Prism redrawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Prism unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
