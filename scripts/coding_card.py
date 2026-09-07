"""Small, dependency-free coding cards. Only aggregated public-facing fields."""
from html import escape

THEMES = {
    'light': ('#ffffff','#1f2328','#59636e','#d1d9e0','#eff2f5','#2da44e'),
    'dark': ('#0d1117','#f0f6fc','#b1bac4','#3d444d','#212830','#3fb950'),
}


def card(data, theme, duration, label):
    bg,ink,muted,border,track,accent=THEMES[theme]
    total=float(data['total_seconds'])
    rows=sorted(data.get('languages',[]),key=lambda x:float(x['total_seconds']),reverse=True)[:4]
    empty=total == 0
    height=156 if empty else 126+len(rows)*30
    def text(x,y,value,size=15,color=ink,extra=''):
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" viewBox="0 0 480 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">最近七天的編程活動</title>',
        f'<desc id="desc">{escape("等待第一筆編程記錄" if empty else "總時長 " + duration(total))}</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif}</style>',
        f'<rect x=".5" y=".5" width="479" height="{height-1}" rx="8" fill="{bg}" stroke="{border}"/>',
        text(240,36,'最近七天',20,extra='font-weight="600" text-anchor="middle"')]
    if empty:
        parts += [text(240,82,'等待第一筆編程記錄',16,extra='text-anchor="middle"'),text(240,116,'每一次動手，都是一點進展。',14,muted,'text-anchor="middle"')]
    else:
        parts += [text(240,64,'編程時間  '+duration(total),15,muted,'text-anchor="middle"')]
        for i,row in enumerate(rows):
            y=101+i*30
            percent=min(100,float(row['percent']))
            parts += [text(24,y,('WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:15])),
                f'<rect x="170" y="{y-10}" width="180" height="7" rx="3.5" fill="{track}"/>',
                f'<rect x="170" y="{y-10}" width="{180*percent/100:.2f}" height="7" rx="3.5" fill="{accent}"/>',
                text(456,y,f'{percent:.1f}%',14,muted,'text-anchor="end"')]
        parts += [text(240,height-18,str(data['start'])[:10]+' — '+str(data['end'])[:10]+' · 含今天',12,muted,'text-anchor="middle"')]
    return ''.join(parts)+'</svg>\n'
