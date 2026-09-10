import { readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { traditionalMarkup } from './traditional.mjs'
const root = new URL('../', import.meta.url)
const read = path => readFile(new URL(path, root), 'utf8')
let readme = await read('README.md')
const file = readme.match(/src="(assets\/netease-[a-f0-9]+\.svg)" alt="Recently played on NetEase Cloud Music"/)?.[1]
if (!file) throw Error('NetEase card missing')
const svg = traditionalMarkup(await read(file))
const next = `assets/netease-${createHash('sha256').update(svg).digest('hex').slice(0, 12)}.svg`
await writeFile(new URL(next, root), svg)
readme = readme.replace(file, next).replace(/(<a name="music-links"><\/a>[\s\S]*?<\/details>)/, part => traditionalMarkup(part))
await writeFile(new URL('README.md', root), readme)
