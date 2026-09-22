"""A compact, responsive weekly report built from aggregated activity only.

Drawn like the rest of the profile: hairlines on a bare background, one accent
(the header's green) for the single thing worth finding first, serif italic
headings and serif figures. Solid green columns, a five-colour legend and a
filled panel made it the loudest block on a page of line work.
"""
from html import escape
from typeface import FIGURES,ITALIC,faces

THEMES = {
    'light': dict(bg='none',ink='#1f2328',muted='#59636e',border='#d1d9e0',line='#59636e',accent='#2da44e'),
    'dark': dict(bg='none',ink='#f0f6fc',muted='#b1bac4',border='#30363d',line='#b1bac4',accent='#3fb950'),
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
    def line(x,y,x2,y2,color=None,extra=''):
        parts.append(f'<path d="M{x},{y}H{x2}" fill="none" stroke="{color or t["border"]}" {extra}/>')
    start=str(data.get('start',''))[:10]
    end=str(data.get('end',''))[:10]
    rows=sorted(data.get('languages',[]),key=lambda r:float(r['total_seconds']),reverse=True)[:4]
    rest=max(0,total-sum(float(r['total_seconds']) for r in rows))
    if rest>0:
        from update_wakatime import merge_remainder
        rows=merge_remainder(rows,rest,total)
    alt=['Recent activity from the last seven days', 'Waiting for the first activity record' if total==0 else 'Total time '+duration(total)]
    alt.extend(f'{label(r["name"])} {duration(r["total_seconds"])} {r["percent"]:.1f}%' for r in rows)
    alt.extend(f'{d["date"]} {duration(d["total_seconds"])}' for d in days)
    if has_ai:
        alt.extend(f'{key}: {value}' for key,value in ai.items() if value is not None)
    parts.extend([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Weekly activity snapshot</title>',
        f'<desc id="desc">{escape(";".join(alt))}</desc>',
        '<style>'+faces('Chiron Italic','Chiron Figures')+'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}'
        f'.serif{{font-family:{ITALIC}}}.number{{font-family:{FIGURES}}}</style>'])
    rect(.5,.5,width-1,height-1,t['bg'],12,f'stroke="{t["border"]}"')
    text(pad,44,'Last 7 days',31,extra='class="serif"')
    text(width-pad,40,'Activity snapshot',15,t['muted'],'text-anchor="end"')
    text(pad,70,f'{start} — {end}',15,t['muted'])
    if not mobile:
        text(width-pad,70,'Asia/Hong_Kong · Includes today',14,t['muted'],'text-anchor="end"')
    line(pad,88,width-pad,88)
    if total==0:
        text(pad,125,'Waiting for the first activity record',20)
        text(pad,155,'Every small step is progress.',17,t['muted'])
        return ''.join(parts)+'</svg>\n'
    text(pad,130,duration(total),36,extra='class="number"')
    active=sum(d['total_seconds']>0 for d in days)
    text(pad,157,f'Active time · {active} / 7 days tracked' if days else 'Activity time',15,t['muted'])
    # Slim daily columns on a shared zero baseline: only the peak takes the accent,
    # and today is a dashed outline because it is incomplete.
    chart_width=width-2*pad if mobile else 286
    base=246 if mobile else 283
    chart_height=64 if mobile else 91
    peak=max((d['total_seconds'] for d in days),default=0)
    step=chart_width/7
    line(pad,base,pad+chart_width,base)
    for i,day in enumerate(days):
        seconds=day['total_seconds']
        bar_height=chart_height*seconds/peak if peak else 0
        bw=min(8,step*.22)
        x=pad+i*step+(step-bw)/2
        is_today=day['date']==end
        if is_today:
            rect(x,base-max(2,bar_height),bw,max(2,bar_height),'none',bw/2,
                 f'stroke="{t["line"]}" stroke-opacity=".7" stroke-dasharray="2 2"')
        else:
            top=peak and seconds==peak
            rect(x,base-max(2,bar_height),bw,max(2,bar_height),t['accent'] if top else t['line'],bw/2,
                 '' if top else 'fill-opacity=".5"')
        text(x+bw/2,base+24,day['date'][5:].replace('-','/'),14,t['muted'],'text-anchor="middle"')
    if days:
        peak_day=max(days,key=lambda d:d['total_seconds'])
        text(pad+chart_width,180 if mobile else 179,'Peak '+duration(peak_day['total_seconds']),14,t['muted'],'text-anchor="end"')
    # Each language has its actual duration, share, and a proportional hairline;
    # the leading one alone is inked in the accent.
    lx=pad if mobile else 360
    right=width-pad
    heading=313 if mobile else 124
    text(lx,heading,'Language distribution',22,extra='class="serif"')
    text(right,heading,'Time / share',14,t['muted'],'text-anchor="end"')
    for i,row in enumerate(rows):
        y=heading+32+i*34
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:18]
        percent=min(100,float(row['percent']))
        text(lx,y,name,17)
        text(right-86,y,duration(row['total_seconds']),17,t['muted'],'text-anchor="end" class="number"')
        text(right,y,f'{percent:.1f}%',17,t['ink'],'text-anchor="end" class="number"')
        line(lx,y+10,right,y+10)
        line(lx,y+10,lx+(right-lx)*percent/100,y+10,t['accent'] if i==0 else t['line'],
             'stroke-width="2" stroke-linecap="round"'+('' if i==0 else ' stroke-opacity=".55"'))
    if has_ai:
        band=530 if mobile else 340
        line(pad,band,right,band)
        text(pad,band+36,'AI collaboration',24,extra='class="serif"')
        if not mobile:
            text(right,band+30,'Same reporting period',14,t['muted'],'text-anchor="end"')
        cost=ai.get('ai_model_total_cost')
        values=[(compact(ai.get('ai_input_tokens'))+' / '+compact(ai.get('ai_output_tokens')),'Input / output tokens'),
            (compact(ai.get('ai_additions'))+' / '+compact(ai.get('ai_prompt_events_total')),'AI additions / prompt count'),
            ('—' if cost is None else f'${cost:,.2f}','AI compute estimate · API pricing')]
        for i,(value,caption) in enumerate(values):
            if mobile:
                y=band+73+i*51
                text(pad,y,caption,15,t['muted'])
                text(right,y,value,22,extra='text-anchor="end" class="number"')
            else:
                x=pad+i*278
                text(x,band+76,value,29,extra='class="number"')
                text(x,band+103,caption,15,t['muted'])
    return ''.join(parts)+'</svg>\n'
