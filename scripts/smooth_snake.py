"""Eat one contribution, stop before the next, then show one short death caption."""
from copy import deepcopy
from math import hypot
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
SPEED=240  # pixels per second; independent of contribution density
RED_HOLD=2
DEATH_HOLD=1.5


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


def motion_css(points,index,cycle):
    """Match the reference's linear CSS translate animation at a fixed speed."""
    frames=[]
    travelled=0
    for i,(x,y) in enumerate(points):
        if i:
            before=points[i-1]
            travelled+=hypot(x-before[0],y-before[1])
        percent=100*travelled/SPEED/cycle
        key=f'{percent:.6f}%'
        if i==len(points)-1:key+=',100%'
        frames.append(f'{key}{{transform:translate({x:g}px,{y:g}px)}}')
    x,y=points[0]
    return (f'.snake-motion.segment-{index}{{transform:translate({x:g}px,{y:g}px);'
        f'animation:move{index} {cycle:.6f}s linear infinite}}'
        f'@keyframes move{index}{{'+''.join(frames)+'}')


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
    lengths=[hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:])]
    def distance_at(time):
        travelled=0
        for i,length in enumerate(lengths):
            if timed[i]<=time<=timed[i+1]:
                return travelled+length*(time-timed[i])/(timed[i+1]-timed[i])
            travelled+=length
        return travelled
    foods=sorted((float(time),name) for name,time in re.findall(r'@keyframes (c\d+)\{([\d.]+)%',original))
    first_distance=distance_at(foods[0][0]) if foods else None
    if len(foods)>1:
        second_distance=distance_at(foods[1][0])
        # For adjacent food cells, stop midway so the second remains uneaten.
        gap=min(24,(second_distance-first_distance)/2)
        stop=second_distance-gap
    else:
        stop=min(sum(lengths)*.85,(first_distance or 40)+96)
    stop=max(1,stop)
    movement=stop/SPEED
    cycle=movement+RED_HOLD+DEATH_HOLD
    travel=movement/cycle
    death=100*travel
    blur_at=100*(movement+RED_HOLD)/cycle
    eat_at=100*first_distance/SPEED/cycle if first_distance is not None else None
    variables=re.search(r':root\{([^}]*)\}',original)
    css=':root{'+(variables[1] if variables else '--ce:#161b22;--cb:#30363d;--cs:#3fb950')+'}'
    dark='--ce:#161b22' in css or '--ce:#0d1117' in css
    css=css.replace('--cs:purple','--cs:#3fb950' if dark else '--cs:#2da44e')
    css+='.c{fill:var(--ce);stroke:var(--cb);stroke-width:1px;width:12px;height:12px}'
    fills=dict(re.findall(r'\.c\.(c\d+)\{fill:([^;]+);',original))
    for name,fill in fills.items():css+=f'.c.{name}{{fill:{fill}}}'
    # Only movement interpolates continuously. The death scene switches once,
    # with a fixed blur over a static snapshot that includes every snake segment.
    css+=f'''
.s{{fill:var(--cs);animation:starve {cycle:.6f}s step-end infinite}}
.still{{display:none}}
.dead-eyes{{opacity:0;animation:cross-eyes {cycle:.6f}s step-end infinite}}
.scene{{animation:alive {cycle:.6f}s step-end infinite}}
.death{{visibility:hidden;animation:dead {cycle:.6f}s step-end infinite}}
@keyframes starve{{0%{{fill:var(--cs)}}{death:.6f}%,100%{{fill:#f85149}}}}
@keyframes cross-eyes{{0%{{opacity:0}}{death:.6f}%,100%{{opacity:1}}}}
@keyframes alive{{0%{{visibility:visible}}{blur_at:.6f}%,100%{{visibility:hidden}}}}
@keyframes dead{{0%{{visibility:hidden}}{blur_at:.6f}%,100%{{visibility:visible}}}}
'''
    if foods:
        fill=fills.get(foods[0][1],'var(--c4)')
        css+=f'.first-food{{animation:eat-first {cycle:.6f}s step-end infinite}}@keyframes eat-first{{0%{{fill:{fill}}}{eat_at:.6f}%,100%{{fill:var(--ce)}}}}'
    css+='@media(prefers-reduced-motion:reduce){.snake-motion,.death{display:none}.still{display:inline}.scene,.s,.first-food{animation:none}}'
    title=ET.Element(f'{{{NS}}}title',{'id':'snake-title'});title.text='蛇吃掉第一塊綠色，在第二塊前變紅並露出叉叉眼，停留兩秒後一起顯示模糊與紅色的蛇饿死了。'
    root.insert(0,title);root.set('role','img');root.set('aria-labelledby','snake-title')
    snake=[node for node in root if node.get('class','').startswith('s ')]
    if not snake:raise ValueError('Missing snake body')
    for node in list(root):
        if node.get('class','').startswith('u '):root.remove(node)
    for node in snake:root.remove(node)
    shape=[]
    for node in list(root):
        if node.get('class')=='c':
            x,y=float(node.get('x')),float(node.get('y'))
            shape.append(f'M{x+2:g},{y:g}h8a2,2 0 0 1 2,2v8a2,2 0 0 1 -2,2h-8a2,2 0 0 1 -2,-2v-8a2,2 0 0 1 2,-2z')
            root.remove(node)
        elif foods and node.get('class')=='c '+foods[0][1]:
            node.set('class',node.get('class')+' first-food')
    if shape:root.insert(2,ET.Element(f'{{{NS}}}path',{'class':'c','d':''.join(shape)}))
    scene=ET.Element(f'{{{NS}}}g',{'class':'scene'})
    for node in list(root):
        if node is not style and node is not title:root.remove(node);scene.append(node)
    root.append(scene)
    # Snapshot contains no animation, including the eaten first cell.
    frozen_grid=[]
    for node in scene:
        item=deepcopy(node)
        if 'first-food' in item.get('class',''):
            item.set('class','c')
        frozen_grid.append(item)
    frozen_snake=[]
    for i,node in enumerate(snake):
        offset=i*16
        route=clipped_path(points,max(1,stop-offset))
        if offset:route=[(points[0][0]+offset,points[0][1])]+route
        group=ET.SubElement(scene,f'{{{NS}}}g',{'class':f'snake-motion segment-{i}'})
        node.set('class','s');group.append(node)
        css+=motion_css(route,i,cycle)
        end=route[-1]
        frozen=ET.Element(f'{{{NS}}}rect',dict(node.attrib))
        frozen.attrib.pop('class');frozen.set('fill','#f85149')
        frozen.set('transform',f'translate({end[0]:g},{end[1]:g})');frozen_snake.append(frozen)
        if i==0:
            eyes=ET.SubElement(group,f'{{{NS}}}path',{
                'class':'dead-eyes','data-face':'crossed-eyes',
                'd':'M4,4l3,3m0,-3l-3,3m5,-3l3,3m0,-3l-3,3',
                'stroke':'#ffffff','stroke-width':'1.2','stroke-linecap':'round','fill':'none'})
            frozen_eyes=deepcopy(eyes)
            frozen_eyes.attrib.pop('class')
            frozen_eyes.set('transform',f'translate({end[0]:g},{end[1]:g})')
            frozen_snake.append(frozen_eyes)
        still=ET.SubElement(scene,f'{{{NS}}}rect',dict(node.attrib));still.set('class','s still');still.set('transform',f'translate({offset},-16)')
    defs=ET.SubElement(root,f'{{{NS}}}defs')
    blur=ET.SubElement(defs,f'{{{NS}}}filter',{'id':'soft-focus','x':'-5%','y':'-15%','width':'110%','height':'130%','color-interpolation-filters':'sRGB'})
    ET.SubElement(blur,f'{{{NS}}}feGaussianBlur',{'stdDeviation':'2.4'})
    death_scene=ET.SubElement(root,f'{{{NS}}}g',{'class':'death'})
    snapshot=ET.SubElement(death_scene,f'{{{NS}}}g',{'filter':'url(#soft-focus)','opacity':'.65','data-layer':'frozen-scene'})
    snapshot.extend(frozen_grid+frozen_snake)
    message=ET.SubElement(death_scene,f'{{{NS}}}text',{'x':'424','y':'64','text-anchor':'middle','font-family':'-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif','font-size':'28','fill':'#f85149','font-weight':'600'})
    message.text='蛇饿死了'
    view=root.get('viewBox')
    if view:
        values=view.split();values[3]='168';root.set('viewBox',' '.join(values));root.set('height','168')
    style.text=css
    return ET.tostring(root,encoding='unicode')


if __name__=='__main__':
    for arg in sys.argv[1:]:
        path=Path(arg);path.write_text(smooth(path.read_text()));print(f'Optimized {path.name}')
