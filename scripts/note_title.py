"""The "lzsm's note" summary, set in the same serif italic as every card title.

GitHub cannot restyle a <summary>, but it can show a picture inside one. There
are no descenders in the phrase, so the baseline sits on the image's bottom
edge and lines up with the disclosure triangle beside it.
"""
from html import escape
import sys
from publish import publish
from typeface import ITALIC,faces

TEXT="lzsm's note"
INK={'light':'#1f2328','dark':'#f0f6fc'}
# About 23px on a desktop and 15px on a phone, like the other titles scaled into
# their columns. The README leaves the size to each image, so both stay exact.
SIZES={False:(23,130,24),True:(15,86,16)}


def card(theme,mobile=False):
    size,width,height=SIZES[mobile]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
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
