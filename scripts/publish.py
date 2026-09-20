"""Content-addressed asset publishing for cards whose markup never changes."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
KEEP=3


def publish(cards,root=None,keep=KEEP):
    """Write each {stem: svg} to assets/<stem>-<digest>.svg and repoint the README."""
    root=Path(root or ROOT)
    assets=root/'assets'
    assets.mkdir(exist_ok=True)
    readme=root/'README.md'
    content=readme.read_text(encoding='utf-8')
    history_file=assets/'versions.json'
    history=json.loads(history_file.read_text()) if history_file.exists() else {}
    for stem,svg in cards.items():
        if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*',stem):
            raise ValueError('Unexpected asset stem')
        digest=hashlib.sha256(svg.encode()).hexdigest()[:12]
        filename=f'{stem}-{digest}.svg'
        named=rf'{re.escape(stem)}-[a-f0-9]+\.svg'
        previous=history.get(stem,[])+sorted(p.name for p in assets.glob(stem+'-*.svg'))
        history[stem]=list(dict.fromkeys([filename]+[n for n in previous if re.fullmatch(named,n)]))[:keep]
        (assets/filename).write_text(svg,encoding='utf-8')
        pattern=rf'assets/{re.escape(stem)}(?:-[a-f0-9]+)?\.svg(?:\?v=[a-f0-9]+)?'
        content,count=re.subn(pattern,'assets/'+filename,content)
        if not count:
            raise ValueError(f'README does not reference {stem}')
        # Only prune this stem: sibling stems own their own history entries.
        for old in assets.glob(stem+'-*.svg'):
            if re.fullmatch(named,old.name) and old.name not in history[stem]:
                old.unlink()
    readme.write_text(content,encoding='utf-8')
    history_file.write_text(json.dumps(history,indent=2)+'\n')
    return content
