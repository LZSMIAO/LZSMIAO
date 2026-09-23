"""A compact, responsive weekly report built from aggregated activity only.

Kept deliberately quiet: a title, one line for the total with seven slim bars
beside it, languages as a single stacked bar with a one-line legend, and the AI
figures as one sentence. A table, a labelled chart and three stat blocks made
the eye jump everywhere. One accent (the header's green) marks the busiest day
and the leading language; everything else is muted ink on the panel fill that
the Recent Activity and music cards share.
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
    def text(x,y,content,size,color=None,extra=''):
        parts.append(f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color or t["ink"]}" {extra}>{content}</text>')
    def span(value,size=None,color=None,cls=None,dx=None):
        attrs=''.join(f' {k}="{v}"' for k,v in (('font-size',size),('fill',color),('class',cls),('dx',dx)) if v is not None)
        return f'<tspan{attrs}>{escape(str(value))}</tspan>'
    alt=['Recent activity from the last seven days','Waiting for the first activity record' if total==0 else 'Total time '+duration(total)]
    alt.extend(f'{label(r["name"])} {duration(r["total_seconds"])} {r["percent"]:.1f}%' for r in rows)
    alt.extend(f'{d["date"]} {duration(d["total_seconds"])}' for d in days)
    if has_ai:
        alt.extend(f'{key}: {value}' for key,value in ai.items() if value is not None)

    text(pad,34 if mobile else 38,'Last 7 days',18,extra='class="serif"')
    period=escape(f'{start} — {end} · Hong Kong' if start else 'Hong Kong')
    if mobile:
        text(pad,54,period,11,t['muted'])
    else:
        text(right,37,period,12,t['muted'],'text-anchor="end"')
    if total==0:
        text(pad,90,escape('Waiting for the first activity record'),15)
        text(pad,112,escape('Every small step is progress.'),12,t['muted'])
        return wrap(parts,width,136,alt,t)

    # The total, with what it means said quietly beside it.
    active=sum(d['total_seconds']>0 for d in days)
    caption=f'{active} of 7 days · {duration(total/7)} a day'
    if mobile:
        text(pad,98,span(duration(total),cls='number'),28)
        text(pad,118,escape(caption),12,t['muted'])
    else:
        text(pad,88,span(duration(total),cls='number')+span(caption,12,t['muted'],dx=14),30)

    # Seven slim bars: no axis, no values, just the shape of the week.
    base=178 if mobile else 88
    tall=40 if mobile else 36
    left=pad if mobile else right-200
    step=(right-left)/7
    peak=max((d['total_seconds'] for d in days),default=0)
    for i,day in enumerate(days):
        seconds=day['total_seconds']
        height=max(2,tall*seconds/peak if peak else 0)
        centre=left+step*(i+.5)
        leads=peak>0 and seconds==peak
        # Today is still running, so it is drawn fainter than the finished days.
        opacity='1' if leads else '.25' if day['date']==end else '.45'
        parts.append(f'<rect x="{centre-3:.1f}" y="{base-height:.1f}" width="6" height="{height:.1f}" rx="3" '
                     f'fill="{t["accent"] if leads else t["line"]}" fill-opacity="{opacity}"/>')
        text(centre,base+15,escape(weekday(day)[0]),10,t['muted'],'text-anchor="middle"')

    # Languages: one stacked bar and a legend beneath it.
    bar=216 if mobile else 124
    x=pad
    span_width=right-pad
    shades=['1','.6','.4','.28','.2']
    for i,row in enumerate(rows):
        share=min(100,float(row['percent']))/100*span_width
        colour=t['accent'] if i==0 else t['line']
        parts.append(f'<rect x="{x:.1f}" y="{bar}" width="{max(0,share-2):.1f}" height="4" rx="2" '
                     f'fill="{colour}" fill-opacity="{shades[min(i,4)] if i else 1}"/>')
        x+=share
    columns=2 if mobile else max(1,len(rows))
    column=span_width/columns
    for i,row in enumerate(rows):
        cx=pad+(i%columns)*column
        cy=bar+24+(i//columns)*22
        name='WGSL' if row['name']=='WebGPU Shading Language' else label(row['name'])[:18]
        colour=t['accent'] if i==0 else t['line']
        parts.append(f'<circle cx="{cx+3:.1f}" cy="{cy-4}" r="3" fill="{colour}" fill-opacity="{shades[min(i,4)] if i else 1}"/>')
        text(cx+12,cy,span(name)+span(f'{min(100,float(row["percent"])):.1f}%',None,t['muted'],'number',6),12)
    bottom=bar+24+((len(rows)-1)//columns)*22+(16 if mobile else 20)
    if not has_ai:
        return wrap(parts,width,bottom+4,alt,t)

    # AI figures as a sentence rather than three competing blocks.
    parts.append(f'<path d="M{pad},{bottom}H{right}" stroke="{t["rule"]}"/>')
    cost=ai.get('ai_model_total_cost')
    tokens=compact(ai.get('ai_input_tokens'))+' / '+compact(ai.get('ai_output_tokens'))
    edits=compact(ai.get('ai_additions'))+' / '+compact(ai.get('ai_prompt_events_total'))
    price='—' if cost is None else f'${cost:,.2f}'
    if mobile:
        text(pad,bottom+28,escape('AI collaboration'),16,extra='class="serif"')
        for i,(caption,value) in enumerate((('Tokens in / out',tokens),('Additions / prompts',edits),('Compute at API pricing',price))):
            y=bottom+54+i*22
            text(pad,y,escape(caption),11,t['muted'])
            text(right,y,span(value,cls='number'),13,extra='text-anchor="end"')
        return wrap(parts,width,bottom+54+2*22+18,alt,t)
    muted=lambda value,dx=None: span(value,12,t['muted'],dx=dx)
    figure=lambda value,dx=None: span(value,13,None,'number',dx)
    text(pad,bottom+30,span('AI collaboration',16,cls='serif')
         +muted('tokens in / out',16)+figure(tokens,6)
         +muted('·',10)+muted('additions / prompts',10)+figure(edits,6)
         +muted('·',10)+figure(price,10)+muted('at API pricing',6),12)
    return wrap(parts,width,bottom+48,alt,t)


def wrap(parts,width,height,alt,t):
    return ''.join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:g}" viewBox="0 0 {width} {height:g}" role="img" aria-labelledby="title desc">',
        '<title id="title">Weekly activity snapshot</title>',
        f'<desc id="desc">{escape(";".join(alt))}</desc>',
        '<style>'+faces('Chiron Italic','Chiron Figures')+'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif;font-variant-numeric:tabular-nums}'
        f'.serif{{font-family:{ITALIC}}}.number{{font-family:{FIGURES}}}</style>',
        f'<rect width="{width}" height="{height:g}" rx="12" fill="{t["panel"]}"/>',
        *parts,'</svg>\n'])
