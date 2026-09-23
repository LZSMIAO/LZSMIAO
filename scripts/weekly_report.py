"""A compact, responsive weekly report built from aggregated activity only.

Drawn like the rest of the profile: hairline rules, one accent (the header's
green) for the single thing worth finding first, serif italic headings and serif
figures. It sits on the same panel fill as the Recent Activity and music cards
below it, so the three blocks read as one set.
"""
from datetime import date
from html import escape
from typeface import FIGURES,ITALIC,faces

THEMES = {
    'light': dict(panel='#f6f8fa',ink='#1f2328',muted='#59636e',rule='#d1d9e0',line='#59636e',accent='#2da44e'),
    'dark': dict(panel='#151b23',ink='#f0f6fc',muted='#b1bac4',rule='#30363d',line='#b1bac4',accent='#3fb950'),
}


def compact(value):
    if value is None:
        return '—'
    for unit,divisor in [('B',1e9),('M',1e6),('K',1e3)]:
        if value>=divisor:
            return f'{value/divisor:.2f}'.rstrip('0').rstrip('.')+unit
    return f'{value:,.0f}'


def languages(data):
    total=float(data['total_seconds'])
    rows=sorted(data.get('languages',[]),key=lambda r:float(r['total_seconds']),reverse=True)[:4]
    rest=max(0,total-sum(float(r['total_seconds']) for r in rows))
    if rest>0:
        from update_wakatime import merge_remainder
        rows=merge_remainder(rows,rest,total)
    # Folding the tail into Other can lift it past rows it used to trail, and the
    # accent belongs to whichever row actually leads.
    return sorted(rows,key=lambda r:float(r['total_seconds']),reverse=True)


def weekday(day):
    return date.fromisoformat(day['date']).strftime('%a')+' '+day['date'][8:10]


def card(data, theme, duration, label, mobile=False):
    t=THEMES[theme]
    width=480 if mobile else 880
    pad=20 if mobile else 24
    right=width-pad
    total=float(data['total_seconds'])
    days=data.get('days',[])
    ai=data.get('ai',{})
    has_ai=any(value and value>0 for value in ai.values())
    start=str(data.get('start',''))[:10]
    end=str(data.get('end',''))[:10]
    rows=languages(data) if total else []
    parts=[]
    def text(x,y,value,size,color=None,extra=''):
        parts.append(f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color or t["ink"]}" {extra}>{escape(str(value))}</text>')
    def rule(x,y,x2):
        parts.append(f'<path d="M{x:g},{y:g}H{x2:g}" stroke="{t["rule"]}"/>')
    end_anchor='text-anchor="end"'
    alt=['Recent activity from the last seven days','Waiting for the first activity record' if total==0 else 'Total time '+duration(total)]
    alt.extend(f'{label(r["name"])} {duration(r["total_seconds"])} {r["percent"]:.1f}%' for r in rows)
    alt.extend(f'{d["date"]} {duration(d["total_seconds"])}' for d in days)
    if has_ai:
        alt.extend(f'{key}: {value}' for key,value in ai.items() if value is not None)

    # Header: serif title on the left, the period on the right (below it on a phone).
    text(pad,38 if mobile else 44,'Last 7 days',22 if mobile else 24,extra='class="serif"')
    period=f'{start} — {end} · Hong Kong' if start else 'Hong Kong'
    if mobile:
        text(pad,60,period,12,t['muted'])
    else:
        text(right,42,period+' · includes today',13,t['muted'],end_anchor)
    top=76 if mobile else 62
    rule(pad,top,right)
    if total==0:
        text(pad,top+40,'Waiting for the first activity record',18)
        text(pad,top+64,'Every small step is progress.',13,t['muted'])
        return wrap(parts,width,top+88,alt,t)

    # Total and the daily chart side by side; stacked on a phone.
    active=sum(d['total_seconds']>0 for d in days)
    text(pad,top+(46 if mobile else 56),duration(total),36 if mobile else 40,extra='class="number"')
    if mobile:
        text(pad,top+70,f'Active on {active} of 7 days · average {duration(total/7)}',12,t['muted'])
    else:
        text(pad,top+82,f'Active on {active} of 7 days',13,t['muted'])
        text(pad,top+102,f'Daily average {duration(total/7)}',13,t['muted'])
    left=pad if mobile else pad+300
    base=top+(170 if mobile else 128)
    tall=64 if mobile else 80
    peak=max((d['total_seconds'] for d in days),default=0)
    step=(right-left)/7 if days else 0
    if days:
        rule(left,base,right)
    for i,day in enumerate(days):
        seconds=day['total_seconds']
        height=max(2,tall*seconds/peak if peak else 0)
        centre=left+step*(i+.5)
        leads=peak>0 and seconds==peak
        colour=t['accent'] if leads else t['line']
        if day['date']==end:
            # Today is still running, so it is outlined rather than filled.
            parts.append(f'<rect x="{centre-5.5:.1f}" y="{base-height+.5:.1f}" width="11" height="{height-.5:.1f}" rx="2" '
                         f'fill="none" stroke="{colour}" stroke-opacity=".8" stroke-dasharray="2 2"/>')
        else:
            fade='' if leads else ' fill-opacity=".4"'
            parts.append(f'<rect x="{centre-6:.1f}" y="{base-height:.1f}" width="12" height="{height:.1f}" rx="2" '
                         f'fill="{colour}"{fade}/>')
        if leads:
            text(centre,base-height-8,duration(seconds),12 if mobile else 13,extra='class="number" text-anchor="middle"')
        text(centre,base+(18 if mobile else 20),weekday(day),11 if mobile else 12,t['muted'],'text-anchor="middle"')

    # Languages as a table: name, a proportional hairline, time and share.
    top=base+(34 if mobile else 38)
    rule(pad,top,right)
    text(pad,top+30 if mobile else top+32,'Languages',18 if mobile else 19,extra='class="serif"')
    text(right,top+30,'Time · share',12,t['muted'],end_anchor)
    first=top+(60 if mobile else 62)
    gap=36 if mobile else 30
    # (start, end, offset from the baseline): under the row on a phone, inline on a desktop.
    x,x2,dy=(pad,right,10) if mobile else (pad+160,right-200,-5)
    for i,row in enumerate(rows):
        y=first+i*gap
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:18]
        percent=min(100,float(row['percent']))
        text(pad,y,name,14)
        text(right-(70 if mobile else 100),y,duration(row['total_seconds']),14,t['muted'],'class="number" '+end_anchor)
        text(right,y,f'{percent:.1f}%',14,extra='class="number" '+end_anchor)
        rule(x,y+dy,x2)
        fade='' if i==0 else ' fill-opacity=".55"'
        parts.append(f'<rect x="{x}" y="{y+dy-1.5:g}" width="{(x2-x)*percent/100:.1f}" height="3" rx="1.5" '
                     f'fill="{t["accent"] if i==0 else t["line"]}"{fade}/>')
    bottom=first+(len(rows)-1)*gap+(26 if mobile else 22)
    if not has_ai:
        return wrap(parts,width,bottom+(0 if mobile else 2),alt,t)

    rule(pad,bottom,right)
    text(pad,bottom+30 if mobile else bottom+32,'AI collaboration',18 if mobile else 19,extra='class="serif"')
    text(right,bottom+30,'Same period',12,t['muted'],end_anchor)
    cost=ai.get('ai_model_total_cost')
    values=[(compact(ai.get('ai_input_tokens'))+' / '+compact(ai.get('ai_output_tokens')),'Input / output tokens'),
        (compact(ai.get('ai_additions'))+' / '+compact(ai.get('ai_prompt_events_total')),'AI additions / prompts'),
        ('—' if cost is None else f'${cost:,.2f}','Compute estimate · API pricing')]
    for i,(value,caption) in enumerate(values):
        if mobile:
            y=bottom+62+i*30
            text(pad,y,caption,12,t['muted'])
            text(right,y,value,18,extra='class="number" '+end_anchor)
        else:
            text(pad+i*280,bottom+68,value,24,extra='class="number"')
            text(pad+i*280,bottom+88,caption,12,t['muted'])
    return wrap(parts,width,bottom+(142 if mobile else 108),alt,t)


def wrap(parts,width,height,alt,t):
    return ''.join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:g}" viewBox="0 0 {width} {height:g}" role="img" aria-labelledby="title desc">',
        '<title id="title">Weekly activity snapshot</title>',
        f'<desc id="desc">{escape(";".join(alt))}</desc>',
        '<style>'+faces('Chiron Italic','Chiron Figures')+'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}'
        f'.serif{{font-family:{ITALIC}}}.number{{font-family:{FIGURES}}}</style>',
        f'<rect width="{width}" height="{height:g}" rx="12" fill="{t["panel"]}"/>',
        *parts,'</svg>\n'])
