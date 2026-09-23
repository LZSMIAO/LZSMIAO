"""The profile's tagline, set as an SVG so it scales with the column.

As a Markdown heading it stayed at GitHub's fixed 24px while every card beside
it shrank on a phone, and it drew a rule underneath. Here the English is in the
serif italic and the Chinese in Chiron Sung HK, each broken by hand per width.
The Chinese face is subset to this sentence: change CHINESE, then rerun
scripts/fonts/build.py (with its TAGLINE updated) before this script.
"""
from html import escape
import sys
from publish import publish
from typeface import ITALIC,TAGLINE,faces

ENGLISH='Words are but a vessel, a river — unknowing of what they bear, they only flow on.'
CHINESE='文字只是載體 只是河流 他對自己所運載的意味並不知曉 他只是一味得流淌'
# Line breaks fall on the sentence's own pauses, never mid-phrase.
LINES={
    False: (['Words are but a vessel, a river —','unknowing of what they bear, they only flow on.'],
            [CHINESE]),
    True: (['Words are but a vessel, a river —','unknowing of what they bear,','they only flow on.'],
           ['文字只是載體 只是河流','他對自己所運載的意味並不知曉 他只是一味得流淌']),
}
THEMES={
    'light': dict(ink='#1f2328',muted='#59636e'),
    'dark': dict(ink='#f0f6fc',muted='#b1bac4'),
}


def card(theme,mobile=False):
    t=THEMES[theme]
    width=480 if mobile else 880
    english,chinese=LINES[mobile]
    size,step=(27,36) if mobile else (30,40)
    y=34
    parts=[]
    for line in english:
        parts.append(f'<text x="0" y="{y}" font-size="{size}" fill="{t["ink"]}" class="en">{escape(line)}</text>')
        y+=step
    y+=4
    for line in chinese:
        parts.append(f'<text x="1" y="{y}" font-size="17" fill="{t["muted"]}" class="zh" letter-spacing="1">{escape(line)}</text>')
        y+=28
    height=y-14
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(ENGLISH+" "+CHINESE,quote=True)}">'
            f'<style>{faces("Chiron Italic","Chiron Tagline")}.en{{font-family:{ITALIC}}}.zh{{font-family:{TAGLINE}}}</style>'
            +''.join(parts)+'</svg>\n')


def main():
    publish({'tagline-'+theme+('-mobile' if mobile else ''):card(theme,mobile)
             for mobile in (False,True) for theme in ('light','dark')})
    print('Tagline redrawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Tagline unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
