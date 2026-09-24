"""Rebuild the embedded subsets of Chiron Sung HK.

GitHub shows profile SVGs through <img>, which cannot fetch fonts, so the face
has to travel inside each SVG as a data URI. The full variable font is ~50 MB of
CJK outlines; printable ASCII at one fixed weight is ~17 KB.

    pip install fonttools brotli
    python3 scripts/fonts/build.py ~/Library/Fonts
    python3 scripts/fonts/build.py /tmp --only chiron-tagline.woff2

The tagline Action runs the second form after downloading the upright face from
google/fonts, so the Chinese subset always matches tagline.txt.
"""
from pathlib import Path
import sys
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE=Path(__file__).resolve().parent
TEXT=''.join(chr(c) for c in range(0x20,0x7f))+'·—…’“”'
sys.path.insert(0,str(HERE.parent))
from tagline import read as read_tagline
# The tagline's Chinese line ships only the characters it uses.
TAGLINE=read_tagline()[1].replace('|',' ')
FACES={
    'chiron-italic.woff2': ('ChironSungHK-Italic-VariableFont_wght.ttf',500,TEXT),
    'chiron-figures.woff2': ('ChironSungHK-VariableFont_wght.ttf',500,TEXT),
    'chiron-tagline.woff2': ('ChironSungHK-VariableFont_wght.ttf',500,TAGLINE),
    # The drift bottle's opening quote, at the face's lightest weight.
    'chiron-quote.woff2': ('ChironSungHK-VariableFont_wght.ttf',200,'“”'),
}


def main(source,only=None):
    for name,(file,weight,text) in FACES.items():
        if only and name!=only:
            continue
        font=TTFont(Path(source)/file)
        options=subset.Options()
        options.layout_features=['kern','liga','tnum','lnum','pnum']
        options.name_IDs=['*']
        options.notdef_outline=True
        # Subset before instancing: pinning the axis on every CJK glyph is minutes of waste.
        tool=subset.Subsetter(options)
        tool.populate(text=text)
        tool.subset(font)
        font=instantiateVariableFont(font,{'wght':weight})
        font.flavor='woff2'
        font.save(HERE/name)
        print(name,(HERE/name).stat().st_size,'bytes')
        if name=='chiron-italic.woff2':
            advances(font)


def advances(font):
    """Glyph widths in em, so the tagline can wrap English without fonttools."""
    import json
    cmap=font.getBestCmap()
    upm=font['head'].unitsPerEm
    table={chr(code):round(font['hmtx'][glyph][0]/upm,4) for code,glyph in sorted(cmap.items())}
    (HERE/'italic-advances.json').write_text(json.dumps(table,ensure_ascii=False,indent=0)+'\n')


if __name__=='__main__':
    args=sys.argv[1:]
    only=args[args.index('--only')+1] if '--only' in args else None
    folders=[a for a in args if not a.startswith('--') and a!=only]
    main(folders[0] if folders else Path.home()/'Library/Fonts',only)
