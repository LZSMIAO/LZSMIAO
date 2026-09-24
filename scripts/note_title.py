"""The "lzsm's note" summary, set in the same serif italic as every card title.

GitHub cannot restyle a <summary>, but it can show a picture inside one. A
fixed-size picture drifted against the other titles, which scale with the
column, so this one scales too: the README shows it at 94% of the column (the
rest is room for the disclosure triangle) and the canvas is 94% of the other
cards' width, so its 24px (20px on phones) lands at exactly their size at any
width. No descenders in the phrase, so the baseline is the image's bottom edge.
"""
from html import escape
import sys
from publish import publish
from typeface import ITALIC,faces

TEXT="lzsm's note"
INK={'light':'#1f2328','dark':'#f0f6fc'}
SHARE=.94
# (font size, card width it matches, canvas height)
SIZES={False:(24,880,24),True:(20,480,20)}


def card(theme,mobile=False):
    size,card_width,height=SIZES[mobile]
    width=round(card_width*SHARE,1)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height}" viewBox="0 0 {width:g} {height}" '
            f'role="img" aria-label="{escape(TEXT,quote=True)}"><style>{faces("Chiron Italic")}text{{font-family:{ITALIC}}}</style>'
            f'<text x="1" y="{height-1}" font-size="{size}" fill="{INK[theme]}">{escape(TEXT)}</text></svg>\n')


def main():
    publish({'note-title-'+theme+('-mobile' if mobile else ''):card(theme,mobile)
             for mobile in (False,True) for theme in ('light','dark')})
    print('Note title drawn.')


if __name__=='__main__':
    try:
        main()
    except (ValueError,KeyError,OSError) as error:
        print(f'Note title unchanged ({type(error).__name__}).',file=sys.stderr)
        sys.exit(1)
