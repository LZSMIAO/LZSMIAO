"""Centered weekly overview with separate desktop and narrow-screen layouts."""
from html import escape

THEMES = {
    'light': ('#ffffff','#1f2328','#59636e','#d1d9e0','#eff2f5','#2da44e'),
    'dark': ('#0d1117','#f0f6fc','#b1bac4','#3d444d','#212830','#3fb950'),
}


def card(data, theme, duration, label, mobile=False):
    bg,ink,muted,border,track,accent=THEMES[theme]
    total=float(data['total_seconds'])
    rows=sorted(data.get('languages',[]),key=lambda x:float(x['total_seconds']),reverse=True)[:4]
    empty=total==0
    width=360 if mobile else 640
    row_gap=58 if mobile else 42
    height=190 if empty else 182+len(rows)*row_gap
    center=width/2
    def text(x,y,value,size=18,color=ink,extra=''):
        return f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Recent activity from the last seven days</title>',
        f'<desc id="desc">{escape("Waiting for the first activity record" if empty else "Total time " + duration(total))}</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}</style>',
        f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="10" fill="{bg}" stroke="{border}"/>',
        text(center,50,'Last 7 days',26,extra='font-weight="600" text-anchor="middle"')]
    if empty:
        parts += [text(center,105,'Waiting for the first activity record',18,extra='text-anchor="middle"'),text(center,145,'Every small step is progress.',16,muted,'text-anchor="middle"')]
    else:
        parts += [text(center,88,'Activity time  '+duration(total),18,muted,'text-anchor="middle"')]
        for i,row in enumerate(rows):
            y=142+i*row_gap
            percent=min(100,float(row['percent']))
            name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:15]
            left=28 if mobile else 40
            bar_x=28 if mobile else 218
            bar_y=y+16 if mobile else y-11
            bar_width=304 if mobile else 270
            parts += [text(left,y,name),
                f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="8" rx="4" fill="{track}"/>',
                f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width*percent/100:.2f}" height="8" rx="4" fill="{accent}"/>',
                text(width-left,y,f'{percent:.1f}%',18,muted,'text-anchor="end"')]
        parts += [text(center,height-26,str(data['start'])[:10]+' — '+str(data['end'])[:10]+' · Includes today',14,muted,'text-anchor="middle"')]
    return ''.join(parts)+'</svg>\n'
