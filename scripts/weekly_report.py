"""A compact, responsive weekly report built from aggregated activity only.

Drawn like the rest of the profile: no frame, hairline rules, one accent (the
header's green) for the single thing worth finding first, serif italic headings
and serif figures. Text sits on the column edge so it lines up with the page's
own headings instead of floating inside a box.
"""
from datetime import date
from html import escape
from typeface import FIGURES,ITALIC,faces

THEMES = {
    'light': dict(ink='#1f2328',muted='#59636e',rule='#d1d9e0',line='#59636e',accent='#2da44e'),
    'dark': dict(ink='#f0f6fc',muted='#b1bac4',rule='#30363d',line='#b1bac4',accent='#3fb950'),
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
    text(0,30 if mobile else 34,'Last 7 days',26 if mobile else 30,extra='class="serif"')
    period=f'{start} — {end} · Hong Kong' if start else 'Hong Kong'
    if mobile:
        text(0,54,period,13,t['muted'])
    else:
        text(width,32,period+' · includes today',14,t['muted'],end_anchor)
    top=72 if mobile else 54
    rule(0,top,width)
    if total==0:
        text(0,top+44,'Waiting for the first activity record',20)
        text(0,top+72,'Every small step is progress.',14,t['muted'])
        return wrap(parts,width,top+92,alt)

    # Total and the daily chart side by side; stacked on a phone.
    active=sum(d['total_seconds']>0 for d in days)
    text(0,top+(56 if mobile else 74),duration(total),44 if mobile else 50,extra='class="number"')
    if mobile:
        text(0,top+82,f'Active on {active} of 7 days · average {duration(total/7)}',13,t['muted'])
    else:
        text(0,top+104,f'Active on {active} of 7 days',14,t['muted'])
        text(0,top+126,f'Daily average {duration(total/7)}',14,t['muted'])
    left=0 if mobile else 330
    base=top+(198 if mobile else 152)
    tall=76 if mobile else 110
    peak=max((d['total_seconds'] for d in days),default=0)
    step=(width-left)/7 if days else 0
    if days:
        rule(left,base,width)
    for i,day in enumerate(days):
        seconds=day['total_seconds']
        height=max(2,tall*seconds/peak if peak else 0)
        centre=left+step*(i+.5)
        leads=peak>0 and seconds==peak
        colour=t['accent'] if leads else t['line']
        if day['date']==end:
            # Today is still running, so it is outlined rather than filled.
            parts.append(f'<rect x="{centre-6.5:.1f}" y="{base-height+.5:.1f}" width="13" height="{height-.5:.1f}" rx="2" '
                         f'fill="none" stroke="{colour}" stroke-opacity=".8" stroke-dasharray="2 2"/>')
        else:
            fade='' if leads else ' fill-opacity=".4"'
            parts.append(f'<rect x="{centre-7:.1f}" y="{base-height:.1f}" width="14" height="{height:.1f}" rx="2" '
                         f'fill="{colour}"{fade}/>')
        if leads:
            text(centre,base-height-9,duration(seconds),13 if mobile else 14,extra='class="number" text-anchor="middle"')
        text(centre,base+(20 if mobile else 22),weekday(day),12 if mobile else 13,t['muted'],'text-anchor="middle"')

    # Languages as a table: name, a proportional hairline, time and share.
    top=base+(42 if mobile else 50)
    rule(0,top,width)
    text(0,top+(34 if mobile else 36),'Languages',21 if mobile else 22,extra='class="serif"')
    text(width,top+34,'Time · share',13,t['muted'],end_anchor)
    first=top+(70 if mobile else 74)
    gap=40 if mobile else 36
    # (start, end, offset from the baseline): under the row on a phone, inline on a desktop.
    x,x2,dy=(0,width,11) if mobile else (190,660,-5)
    for i,row in enumerate(rows):
        y=first+i*gap
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:18]
        percent=min(100,float(row['percent']))
        text(0,y,name,15)
        text(width-(80 if mobile else 110),y,duration(row['total_seconds']),15,t['muted'],'class="number" '+end_anchor)
        text(width,y,f'{percent:.1f}%',15,extra='class="number" '+end_anchor)
        rule(x,y+dy,x2)
        fade='' if i==0 else ' fill-opacity=".55"'
        parts.append(f'<rect x="{x}" y="{y+dy-1.5:g}" width="{(x2-x)*percent/100:.1f}" height="3" rx="1.5" '
                     f'fill="{t["accent"] if i==0 else t["line"]}"{fade}/>')
    bottom=first+(len(rows)-1)*gap+(30 if mobile else 26)
    if not has_ai:
        return wrap(parts,width,bottom,alt)

    rule(0,bottom,width)
    text(0,bottom+(34 if mobile else 36),'AI collaboration',21 if mobile else 22,extra='class="serif"')
    text(width,bottom+34,'Same period',13,t['muted'],end_anchor)
    cost=ai.get('ai_model_total_cost')
    values=[(compact(ai.get('ai_input_tokens'))+' / '+compact(ai.get('ai_output_tokens')),'Input / output tokens'),
        (compact(ai.get('ai_additions'))+' / '+compact(ai.get('ai_prompt_events_total')),'AI additions / prompts'),
        ('—' if cost is None else f'${cost:,.2f}','Compute estimate · API pricing')]
    for i,(value,caption) in enumerate(values):
        if mobile:
            y=bottom+72+i*34
            text(0,y,caption,13,t['muted'])
            text(width,y,value,20,extra='class="number" '+end_anchor)
        else:
            text(i*300,bottom+84,value,30,extra='class="number"')
            text(i*300,bottom+108,caption,13,t['muted'])
    return wrap(parts,width,bottom+(162 if mobile else 118),alt)


def wrap(parts,width,height,alt):
    return ''.join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:g}" viewBox="0 0 {width} {height:g}" role="img" aria-labelledby="title desc">',
        '<title id="title">Weekly activity snapshot</title>',
        f'<desc id="desc">{escape(";".join(alt))}</desc>',
        '<style>'+faces('Chiron Italic','Chiron Figures')+'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}'
        f'.serif{{font-family:{ITALIC}}}.number{{font-family:{FIGURES}}}</style>',
        *parts,'</svg>\n'])
