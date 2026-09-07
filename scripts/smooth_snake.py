"""A short SVG story: the snake runs out of energy just before its first meal."""
from copy import deepcopy
from math import hypot
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
CYCLE=10
TRAVEL=.35


def clipped_path(points,distance):
    result=[points[0]]
    for a,b in zip(points,points[1:]):
        length=hypot(b[0]-a[0],b[1]-a[1])
        if length==0:continue
        if distance<=length:
            result.append(tuple(a[j]+(b[j]-a[j])*distance/length for j in (0,1)))
            break
        result.append(b);distance-=length
    return result


def rounded_path(points,radius=4):
    def xy(p):return f'{p[0]:g},{p[1]:g}'
    commands=['M'+xy(points[0])]
    for a,p,b in zip(points,points[1:],points[2:]):
        incoming=hypot(p[0]-a[0],p[1]-a[1])
        outgoing=hypot(b[0]-p[0],b[1]-p[1])
        if min(incoming,outgoing)==0:continue
        r=min(radius,incoming/3,outgoing/3)
        entry=tuple(p[j]+(a[j]-p[j])*r/incoming for j in (0,1))
        leave=tuple(p[j]+(b[j]-p[j])*r/outgoing for j in (0,1))
        commands+=['L'+xy(entry),'Q'+xy(p)+' '+xy(leave)]
    commands.append('L'+xy(points[-1]))
    return ' '.join(commands)


def smooth(svg):
    root=ET.fromstring(svg)
    style=root.find(f'{{{NS}}}style')
    original=style.text if style is not None else ''
    match=re.search(r'@keyframes s0\{((?:[^{}]*\{[^{}]*\})+)\}',original)
    if not match:raise ValueError('Unsupported snake animation: missing head keyframes')
    frames=[]
    for times,x,y in re.findall(r'([\d.% ,]+)\{transform:translate\((-?[\d.]+)px,(-?[\d.]+)px\)\}',match[1]):
        frames.extend((float(time.strip('% ')),float(x),float(y)) for time in times.split(','))
    frames.sort()
    points=[];timed=[]
    for time,x,y in frames:
        if not points or points[-1]!=(x,y):points.append((x,y));timed.append(time)
    if len(points)<2:raise ValueError('Empty snake path')
    # Original contribution keyframes mark the instant the first food is eaten.
    food_times=[float(value) for value in re.findall(r'@keyframes c\d+\{([\d.]+)%',original)]
    first_food=min(food_times) if food_times else None
    travelled=0;food_distance=None
    for i,(a,b) in enumerate(zip(points,points[1:])):
        length=hypot(b[0]-a[0],b[1]-a[1])
        if first_food is not None and timed[i]<=first_food<=timed[i+1]:
            food_distance=travelled+length*(first_food-timed[i])/(timed[i+1]-timed[i])
            break
        travelled+=length
    if food_distance is None:food_distance=min(travelled,180)
    stop=max(1,food_distance-24)
    # Use original palette and food colors, with no cell-clearing animation.
    variables=re.search(r':root\{([^}]*)\}',original)
    css=':root{'+(variables[1] if variables else '--ce:#161b22;--cb:#30363d;--cs:#3fb950')+'}'
    dark='--ce:#161b22' in css or '--ce:#0d1117' in css
    ink='#f0f6fc' if dark else '#1f2328'
    muted='#b1bac4' if dark else '#59636e'
    css=css.replace('--cs:purple','--cs:#3fb950' if dark else '--cs:#2da44e')
    css+='.c{fill:var(--ce);stroke:var(--cb);stroke-width:1px;width:12px;height:12px}'
    for name,fill in re.findall(r'(\.c\.c\d+)\{fill:([^;]+);',original):css+=name+'{fill:'+fill+'}'
    css+='''
.s{fill:var(--cs);animation:starve 10s linear infinite}
.still{display:none}
.scene{animation:scene-cycle 10s linear infinite}
.snake-motion{animation:snake-cycle 10s linear infinite}
.interlude{opacity:0;animation:interlude-cycle 10s linear infinite}
.message{opacity:0;animation:message-cycle 10s linear infinite}
.dead-eyes{opacity:0;animation:eyes-cycle 10s linear infinite}
@keyframes starve{0%,35%{fill:var(--cs)}40%,100%{fill:#f85149}}
@keyframes scene-cycle{0%,40%,100%{opacity:1}48%,90%{opacity:0}}
@keyframes snake-cycle{0%,94%,100%{opacity:0}6%,87%{opacity:1}}
@keyframes interlude-cycle{0%,40%,100%{opacity:0}48%,90%{opacity:1}}
@keyframes message-cycle{0%,43%,96%,100%{opacity:0;transform:translateY(4px)}49%,86%{opacity:1;transform:translateY(0)}}
@keyframes eyes-cycle{0%,37%,100%{opacity:0}41%,94%{opacity:1}}
@media(prefers-reduced-motion:reduce){.snake-motion,.interlude,.message{display:none}.still{display:inline}.scene,.s{animation:none}}
'''
    style.text=css
    title=ET.Element(f'{{{NS}}}title',{'id':'snake-title'});title.text='蛇還沒吃到綠色格子就餓死了；十秒後重新出發。'
    root.insert(0,title);root.set('role','img');root.set('aria-labelledby','snake-title')
    snake=[node for node in root if node.get('class','').startswith('s ')]
    if not snake:raise ValueError('Missing snake body')
    for node in list(root):
        if node.get('class','').startswith('u '):root.remove(node)
    for node in snake:root.remove(node)
    # Merge empty cells into one static path.
    shape=[]
    for node in list(root):
        if node.get('class')=='c':
            x,y=float(node.get('x')),float(node.get('y'))
            shape.append(f'M{x+2:g},{y:g}h8a2,2 0 0 1 2,2v8a2,2 0 0 1 -2,2h-8a2,2 0 0 1 -2,-2v-8a2,2 0 0 1 2,-2z')
            root.remove(node)
    if shape:root.insert(2,ET.Element(f'{{{NS}}}path',{'class':'c','d':''.join(shape)}))
    scene=ET.Element(f'{{{NS}}}g',{'class':'scene'})
    for node in list(root):
        if node is not style and node is not title:root.remove(node);scene.append(node)
    root.append(scene)
    defs=ET.SubElement(root,f'{{{NS}}}defs')
    blur=ET.SubElement(defs,f'{{{NS}}}filter',{'id':'soft-focus','x':'-10%','y':'-30%','width':'120%','height':'160%','color-interpolation-filters':'sRGB'})
    ET.SubElement(blur,f'{{{NS}}}feGaussianBlur',{'stdDeviation':'2.6'})
    overlay=ET.SubElement(root,f'{{{NS}}}g',{'class':'interlude','aria-hidden':'true'})
    snapshot=ET.SubElement(overlay,f'{{{NS}}}g',{'filter':'url(#soft-focus)','opacity':'.38'})
    for node in scene:snapshot.append(deepcopy(node))
    # Each segment has its own endpoint. They keep their spacing when the head stops.
    for i,node in enumerate(snake):
        offset=i*16
        route=clipped_path(points,max(1,stop-offset))
        if offset:
            initial=(points[0][0]+offset,points[0][1])
            route=[initial]+route
        group=ET.SubElement(root,f'{{{NS}}}g',{'class':'snake-motion'})
        node.set('class','s');group.append(node)
        ET.SubElement(group,f'{{{NS}}}animateMotion',{'path':rounded_path(route),'dur':f'{CYCLE}s','repeatCount':'indefinite','calcMode':'linear','keyPoints':'0;1;1','keyTimes':f'0;{TRAVEL};1'})
        if i==0:
            eyes=ET.SubElement(group,f'{{{NS}}}path',{'class':'dead-eyes','d':'M4,4l3,3m0,-3l-3,3m5,-3l3,3m0,-3l-3,3','stroke':'#ffffff','stroke-width':'1.2','stroke-linecap':'round'})
        still=ET.SubElement(root,f'{{{NS}}}rect',dict(node.attrib));still.set('class','s still');still.set('transform',f'translate({offset},-16)')
    message=ET.SubElement(root,f'{{{NS}}}g',{'class':'message','text-anchor':'middle','font-family':'-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif'})
    for y,value,size,color,weight in [(49,'蛇饿死了。',38,'#f85149','650'),(86,'项目一只手数得过来，实在不够吃。',23,ink,'500'),(115,'还没吃到下一口，就先耗尽了力气。',17,muted,'400')]:
        node=ET.SubElement(message,f'{{{NS}}}text',{'x':'424','y':str(y),'font-size':str(size),'fill':color,'font-weight':weight});node.text=value
    # Remove the space previously reserved for the green progress bar.
    view=root.get('viewBox')
    if view:
        values=view.split();values[3]='168';root.set('viewBox',' '.join(values));root.set('height','168')
    return ET.tostring(root,encoding='unicode')


if __name__=='__main__':
    for arg in sys.argv[1:]:
        path=Path(arg);path.write_text(smooth(path.read_text()));print(f'Optimized {path.name}')
