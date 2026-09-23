"""Rebuild the embedded Latin subsets of Chiron Sung HK. Run locally, never in CI.

GitHub shows profile SVGs through <img>, which cannot fetch fonts, so the face
has to travel inside each SVG as a data URI. The full variable font is ~50 MB of
CJK outlines; printable ASCII at one fixed weight is ~17 KB.

    pip install fonttools brotli
    python3 scripts/fonts/build.py ~/Library/Fonts
"""
from pathlib import Path
import sys
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE=Path(__file__).resolve().parent
TEXT=''.join(chr(c) for c in range(0x20,0x7f))+'·—…’“”'
# The tagline is fixed copy, so its Chinese line ships only the characters it
# uses. Change the sentence in scripts/tagline.py and rebuild.
TAGLINE='文字只是載體 只是河流 他對自己所運載的意味並不知曉 他只是一味得流淌'
FACES={
    'chiron-italic.woff2': ('ChironSungHK-Italic-VariableFont_wght.ttf',500,TEXT),
    'chiron-figures.woff2': ('ChironSungHK-VariableFont_wght.ttf',650,TEXT),
    'chiron-tagline.woff2': ('ChironSungHK-VariableFont_wght.ttf',500,TAGLINE),
}


def main(source):
    for name,(file,weight,text) in FACES.items():
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


if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else Path.home()/'Library/Fonts')
