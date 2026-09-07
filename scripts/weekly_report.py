"""A compact, responsive weekly report built from aggregated activity only."""
from html import escape

THEMES = {
    'light': dict(bg='#ffffff',ink='#1f2328',muted='#59636e',border='#d1d9e0',track='#eff2f5',accent='#238636',soft='#f6f8fa',colors=['#238636','#0969da','#8250df','#9a6700','#59636e']),
    'dark': dict(bg='#0d1117',ink='#f0f6fc',muted='#b1bac4',border='#30363d',track='#212830',accent='#56d364',soft='#151b23',colors=['#56d364','#79c0ff','#d2a8ff','#e3b341','#9198a1']),
}


def compact(value):
    if value is None:
        return '—'
    for unit,divisor in [('B',1e9),('M',1e6),('K',1e3)]:
        if value>=divisor:
            return f'{value/divisor:.2f}'.rstrip('0').rstrip('.')+unit
    return f'{value:,.0f}'


def card(data, theme, duration, label, mobile=False):
    t=THEMES[theme]
    width=480 if mobile else 880
    pad=24 if mobile else 28
    total=float(data['total_seconds'])
    days=data.get('days',[])
    ai=data.get('ai',{})
    has_ai=any(value and value>0 for value in ai.values())
    height=(730 if mobile else 464) if has_ai else (528 if mobile else 338)
    if total==0:
        height=180
    parts=[]
    def text(x,y,value,size=18,color=None,extra=''):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color or t["ink"]}" {extra}>{escape(str(value))}</text>')
    def rect(x,y,w,h,fill,rx=0,extra=''):
        parts.append(f'<rect x="{x}" y="{y}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" fill="{fill}" {extra}/>')
    def line(x,y,x2,y2):
        parts.append(f'<path d="M{x},{y}H{x2}" fill="none" stroke="{t["border"]}"/>')
    start=str(data.get('start',''))[:10]
    end=str(data.get('end',''))[:10]
    rows=sorted(data.get('languages',[]),key=lambda r:float(r['total_seconds']),reverse=True)[:4]
    rest=max(0,total-sum(float(r['total_seconds']) for r in rows))
    if rest>0:
        rows=rows+[{'name':'其他','total_seconds':rest,'percent':100*rest/total}]
    alt=['最近七天的編程活動', '等待第一筆編程記錄' if total==0 else '總時長 '+duration(total)]
    alt.extend(f'{label(r["name"])} {duration(r["total_seconds"])} {r["percent"]:.1f}%' for r in rows)
    alt.extend(f'{d["date"]} {duration(d["total_seconds"])}' for d in days)
    if has_ai:
        alt.extend(f'{key}: {value}' for key,value in ai.items() if value is not None)
    parts.extend([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">LZ · 最近七天編程手記</title>',
        f'<desc id="desc">{escape("；".join(alt))}</desc>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}.number{font-family:ui-monospace,"SFMono-Regular",Consolas,monospace}</style>'])
    rect(.5,.5,width-1,height-1,t['bg'],12,f'stroke="{t["border"]}"')
    text(pad,42,'最近七天',26,extra='font-weight="650"')
    text(width-pad,40,'LZ / 編程手記',17,t['muted'],'text-anchor="end"')
    text(pad,70,f'{start} — {end}',16,t['muted'])
    if not mobile:
        text(width-pad,70,'Asia/Shanghai · 含今天',15,t['muted'],'text-anchor="end"')
    line(pad,88,width-pad,88)
    if total==0:
        text(pad,125,'等待第一筆編程記錄',20)
        text(pad,155,'每一次動手，都是一點進展。',17,t['muted'])
        return ''.join(parts)+'</svg>\n'
    text(pad,128,duration(total),30,extra='font-weight="650" class="number"')
    active=sum(d['total_seconds']>0 for d in days)
    text(pad,155,f'編程時間 · {active} / 7 天有記錄' if days else '編程時間',16,t['muted'])
    # Daily columns use a shared zero baseline; today is outlined because it is incomplete.
    chart_width=width-2*pad if mobile else 286
    base=246 if mobile else 283
    chart_height=64 if mobile else 91
    peak=max((d['total_seconds'] for d in days),default=0)
    step=chart_width/7
    line(pad,base,pad+chart_width,base)
    for i,day in enumerate(days):
        seconds=day['total_seconds']
        bar_height=chart_height*seconds/peak if peak else 0
        x=pad+i*step+step*.18
        bw=step*.64
        is_today=day['date']==end
        fill=t['soft'] if is_today else t['accent']
        rect(x,base-max(2,bar_height),bw,max(2,bar_height),fill,3,f'stroke="{t["accent"]}"' if is_today else '')
        text(x+bw/2,base+24,day['date'][5:].replace('-','/'),14,t['muted'],'text-anchor="middle"')
    if days:
        peak_day=max(days,key=lambda d:d['total_seconds'])
        text(pad+chart_width,180 if mobile else 179,'最高 '+duration(peak_day['total_seconds']),14,t['muted'],'text-anchor="end"')
    # Each language has its actual duration, share, and a proportional colored rule.
    lx=pad if mobile else 360
    right=width-pad
    heading=313 if mobile else 124
    text(lx,heading,'語言分布',18,extra='font-weight="600"')
    text(right,heading,'時長 / 佔比',14,t['muted'],'text-anchor="end"')
    for i,row in enumerate(rows):
        y=heading+32+i*34
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:18]
        percent=min(100,float(row['percent']))
        color=t['colors'][i]
        rect(lx,y-11,7,7,color,2)
        text(lx+17,y,name,18)
        text(right-86,y,duration(row['total_seconds']),16,t['muted'],'text-anchor="end" class="number"')
        text(right,y,f'{percent:.1f}%',16,t['ink'],'text-anchor="end" class="number"')
        rect(lx+17,y+8,right-lx-17,3,t['track'],1.5)
        rect(lx+17,y+8,(right-lx-17)*percent/100,3,color,1.5)
    if has_ai:
        band=530 if mobile else 340
        rect(1,band,width-2,height-band-13,t['soft'])
        rect(1,height-25,width-2,24,t['soft'],11)
        text(pad,band+31,'AI 協作',20,extra='font-weight="600"')
        if not mobile:
            text(right,band+30,'同一統計區間',14,t['muted'],'text-anchor="end"')
        cost=ai.get('ai_model_total_cost')
        values=[(compact(ai.get('ai_input_tokens'))+' / '+compact(ai.get('ai_output_tokens')),'輸入 / 輸出 Tokens'),
            (compact(ai.get('ai_additions'))+' / '+compact(ai.get('ai_prompt_events_total')),'AI 新增行 / 提問次數'),
            ('—' if cost is None else f'${cost:,.2f}','AI 算力估值 · API 價格估算')]
        for i,(value,caption) in enumerate(values):
            if mobile:
                y=band+73+i*51
                text(pad,y,caption,15,t['muted'])
                text(right,y,value,21,extra='text-anchor="end" class="number" font-weight="600"')
            else:
                x=pad+i*278
                text(x,band+72,value,26,extra='class="number" font-weight="600"')
                text(x,band+101,caption,16,t['muted'])
    return ''.join(parts)+'</svg>\n'
