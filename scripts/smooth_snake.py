"""Replace staggered CSS snake transforms with one continuously paced SVG path."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def smooth(svg):
    root = ET.fromstring(svg)
    style = root.find(f'{{{NS}}}style')
    css = style.text
    match = re.search(r'@keyframes s0\{((?:[^{}]*\{[^{}]*\})+)\}', css)
    if not match:
        raise ValueError('Unsupported snake animation: missing head keyframes')
    points = []
    frames = []
    for times, x, y in re.findall(r'([\d.% ,]+)\{transform:translate\((-?[\d.]+)px,(-?[\d.]+)px\)\}', match[1]):
        for time in times.split(','):
            frames.append((float(time.strip('% ')), float(x), float(y)))
    frames.sort()
    for _, x, y in frames:
        if not points or points[-1] != (x, y):
            points.append((x, y))
    if points[-1] != points[0]:
        points.append(points[0])
    distances = [abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(points, points[1:])]
    length = sum(distances)
    if not length:
        raise ValueError('Empty snake path')
    old_ms = float(re.search(r'animation:[^;}]*?([\d.]+)ms', css)[1])
    moving_end = frames[-1][0] / 100
    # 125ms per cell gives corners more breathing room than the original 100ms.
    duration = length / 128
    path = 'M' + ' L'.join(f'{x:g},{y:g}' for x,y in points)
    css = re.sub(r'@keyframes s\d+\{(?:[^{}]*\{[^{}]*\})+\}', '', css)
    css = re.sub(r'\.s\.s\d+\{[^}]*\}', '', css)
    css = re.sub(r'\.s\{[^}]*\}', '.s{fill:var(--cs)}', css)
    css = css.replace(f'{old_ms:g}ms', f'{duration:g}s')
    # Keep contribution-cell clearing synchronized after removing the loop hold.
    def retime(m):
        return f'{min(100, float(m[1])/moving_end):.4f}%'
    css = re.sub(r'([\d.]+)%(?=[,{])', retime, css)
    css = re.sub(r'@media\(prefers-reduced-motion:reduce\)\{.*?\}\}', '', css)
    css += '.still{display:none}@media(prefers-reduced-motion:reduce){.motion{display:none}.still{display:inline}.c,.u{animation:none!important}}'
    style.text = css.replace('--cs:purple', '--cs:#2da44e')
    snake = [node for node in root if node.get('class','').startswith('s ')]
    if not snake:
        raise ValueError('Missing snake body')
    for i,node in enumerate(snake):
        root.remove(node)
        node.set('class','s motion')
        motion = ET.SubElement(node, f'{{{NS}}}animateMotion', {
            'path':path, 'dur':f'{duration:g}s', 'begin':f'{-duration + i * .125:g}s',
            'repeatCount':'indefinite', 'calcMode':'paced',
        })
        root.append(node)
        still=ET.SubElement(root,f'{{{NS}}}rect',dict(node.attrib))
        still.set('class','s still')
        still.set('transform',f'translate({i*16},-16)')
    # Use a single path for the hundreds of static empty grid cells.
    static = [n for n in root if n.get('class') == 'c']
    shape=[]
    for node in static:
        x,y=float(node.get('x')),float(node.get('y'))
        shape.append(f'M{x+2:g},{y:g}h8a2,2 0 0 1 2,2v8a2,2 0 0 1 -2,2h-8a2,2 0 0 1 -2,-2v-8a2,2 0 0 1 2,-2z')
        root.remove(node)
    if shape:
        root.insert(2, ET.Element(f'{{{NS}}}path', {'class':'c','d':''.join(shape)}))
    return ET.tostring(root, encoding='unicode')


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        path=Path(arg)
        path.write_text(smooth(path.read_text()))
        print(f'Optimized {path.name}')
