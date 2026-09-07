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
    editors=sorted(data.get('editors',[]),key=lambda x:float(x['total_seconds']),reverse=True)[:2]
    empty=total == 0
    height=142 if empty else 114+len(rows)*26
    def text(x,y,value,size=15,color=ink,extra=''):
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" viewBox="0 0 480 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">最近七天的編程活動</title>',
        f'<desc id="desc">{escape("等待第一筆編程記錄" if empty else "總時長 " + duration(total))}</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif}</style>',
        f'<rect x=".5" y=".5" width="479" height="{height-1}" rx="8" fill="{bg}" stroke="{border}"/>',
        text(20,31,'最近七天',17,extra='font-weight="600"'),
        text(460,31,'WakaTime',13,muted,'text-anchor="end"')]
    if empty:
        parts += [text(20,71,'等待第一筆編程記錄',16),text(20,105,'從下一次 Qoder 編輯開始累積。',14,muted)]
    else:
        names=' · '.join(label(x['name']) for x in editors)
        parts += [text(20,58,duration(total)+'  ·  '+names,15,muted)]
        for i,row in enumerate(rows):
            y=86+i*26
            percent=min(100,float(row['percent']))
            parts += [text(20,y,label(row['name'])[:15]),
                f'<rect x="166" y="{y-10}" width="180" height="7" rx="3.5" fill="{track}"/>',
                f'<rect x="166" y="{y-10}" width="{180*percent/100:.2f}" height="7" rx="3.5" fill="{accent}"/>',
                text(460,y,f'{percent:.1f}%',14,muted,'text-anchor="end"')]
        parts += [text(20,height-18,str(data['start'])[:10]+' — '+str(data['end'])[:10],12,muted)]
    return ''.join(parts)+'</svg>\n'
