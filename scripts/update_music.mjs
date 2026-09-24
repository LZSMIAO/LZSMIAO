import { createCipheriv, createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { traditional } from './traditional.mjs'

const root = new URL('../', import.meta.url)
const read = path => readFile(new URL(path, root), 'utf8')
const write = (path, value) => writeFile(new URL(path, root), value)
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;')
const shorten = (value, length) => Array.from(value).length > length ? Array.from(value).slice(0, length - 1).join('') + '…' : value
async function request(url, options = {}) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(30000) })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response
}
// The card is one <img> with no <picture> around it, so it follows the reader's
// colour scheme from inside: the same panel fill as the Recent Activity card in
// either theme, instead of a Spotify-black block on a white page.
const italic = (await readFile(new URL('scripts/fonts/chiron-italic.woff2', root))).toString('base64')
export const palette = '.bg{fill:#f6f8fa}.well{fill:#eaeef2}.ink{fill:#1f2328}.muted{fill:#59636e}'
  + '@media(prefers-color-scheme:dark){.bg{fill:#151b23}.well{fill:#212830}.ink{fill:#f0f6fc}.muted{fill:#b1bac4}}'
function frame(title, content) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="445" viewBox="0 0 320 445" role="img" aria-label="${esc(title)}"><style>@font-face{font-family:"Chiron Italic";src:url(data:font/woff2;base64,${italic}) format("woff2")}text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC",sans-serif}.serif{font-family:"Chiron Italic",Georgia,serif}${palette}</style><rect class="bg" width="320" height="445" rx="10"/>${content}</svg>`
}
// Shown at half the column, 17.5/320 matches the 24/880 titles of the full-width cards.
const heading = (title, source) => `<text x="20" y="36" class="ink serif" font-size="17.5">${title}</text><text x="20" y="54" class="muted" font-size="11">${source}</text>`
export function offlineCard(logo) {
  return frame('Spotify — not playing', `${heading('Now playing', 'Spotify')}<image x="275" y="20" width="25" height="25" href="${logo}"/><circle class="well" cx="160" cy="200" r="42"/><image x="139" y="179" width="42" height="42" opacity="0.55" href="${logo}"/><text x="160" y="282" text-anchor="middle" class="ink" font-size="20" font-weight="600">Not playing</text><text x="160" y="306" text-anchor="middle" class="muted" font-size="12">Nothing playing right now</text>`)
}
async function publishCard(platform, svg, transform = value => value) {
  const filename = `assets/${platform}-${createHash('sha256').update(svg).digest('hex').slice(0, 12)}.svg`
  let content = await read('README.md')
  const pattern = platform === 'spotify'
    ? /(<img alt="Spotify now playing" src=")[^"]+(" width="[^"]+">)/
    : /(<img src=")assets\/netease-[^"]+(" alt="Recently played on NetEase Cloud Music")/
  if (!pattern.test(content)) throw new Error('Music card reference missing')
  content = transform(content.replace(pattern, `$1${filename}$2`))
  await write(filename, svg)
  await write('README.md', content)
}
async function spotify() {
  // Kept as a safe no-op for older callers: never overwrite the live endpoint.
  console.log('Spotify is served live by Cloudflare; no repository snapshot written.')
}
function encrypt(key, value) {
  const cipher = createCipheriv('aes-128-cbc', key, '0102030405060708')
  return cipher.update(value, 'utf8', 'base64') + cipher.final('base64')
}
async function netease() {
  const uid = process.env.NETEASE_USER_ID?.trim()
  if (!uid || !/^\d+$/.test(uid)) throw new Error('NETEASE_USER_ID secret is missing')
  const body = new URLSearchParams({
    params: encrypt('TA3YiYCfY2dDJQgg', encrypt('0CoJUm6Qyw8W8jud', JSON.stringify({ uid, type: '1' }))),
    encSecKey: '84ca47bca10bad09a6b04c5c927ef077d9b9f1e37098aa3eac6ea70eb59df0aa28b691b7e75e4f1f9831754919ea784c8f74fbfadf2898b0be17849fd656060162857830e241aba44991601f137624094c114ea8d17bce815b0cd4e5b8e2fbaba978c6d1d14dc3d1faf852bdd28818031ccdaaa13a6018e1024e2aae98844210',
  })
  const data = await (await request('https://music.163.com/weapi/v1/play/record?csrf_token=', {
    method: 'POST', body, headers: { Referer: 'https://music.163.com/', 'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded' },
  })).json()
  if (data.code !== 200 || !Array.isArray(data.weekData)) throw new Error('NetEase weekly data unavailable')
  const tracks = await Promise.all(data.weekData.slice(0, 5).map(async ({ song }) => {
    const id = String(song.id)
    if (!/^\d+$/.test(id) || !song.name || !Array.isArray(song.ar)) throw new Error('Invalid song metadata')
    const artists = song.ar.map(a => ({ id: String(a.id), name: traditional(a.name) }))
    if (artists.some(a => !/^\d+$/.test(a.id) || !a.name)) throw new Error('Invalid artist metadata')
    const url = new URL(song.al.picUrl)
    if (!url.hostname.endsWith('.music.126.net')) throw new Error('Unexpected cover host')
    url.protocol = 'https:'
    url.searchParams.set('param', '160y160')
    const response = await request(url)
    const bytes = Buffer.from(await response.arrayBuffer())
    const type = bytes[0] === 255 && bytes[1] === 216 ? 'image/jpeg'
      : bytes.subarray(0, 8).toString('hex') === '89504e470d0a1a0a' ? 'image/png'
      : bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP' ? 'image/webp' : null
    if (!type || bytes.length > 2000000) throw new Error('Invalid cover image')
    const image = `data:${type};base64,${bytes.toString('base64')}`
    return { id, name: traditional(song.name), artists, image, cover: url.toString() }
  }))
  const previous = await read('assets/netease-clean.svg')
  const logo = previous.match(/<g transform="translate\(275 23\)">.*?<\/g>/)?.[0]
  if (!logo) throw new Error('Existing NetEase logo missing')
  await publishCard('netease', neteaseCard(tracks, logo))
  await write('assets/netease-week.json', weekFile(tracks))
  console.log(`NetEase: updated ${tracks.length} tracks.`)
}
// The card links to a page on the presence Worker that lists these songs, each
// linked, since an <img> on GitHub can carry only one link. No user id in here.
export function weekFile(tracks) {
  return JSON.stringify({ tracks: tracks.map(({ id, name, artists, cover }) => ({ id, name, artists: artists.map(({ id, name }) => ({ id, name })), cover })) }, null, 2) + '\n'
}
export function neteaseCard(tracks, logo) {
  const rows = tracks.map((track, i) => {
    const y = 80 + i * 70
    return `<g><clipPath id="cover${i}"><rect x="20" y="${y}" width="56" height="56" rx="5"/></clipPath><image x="20" y="${y}" width="56" height="56" href="${track.image}" preserveAspectRatio="xMidYMid meet" clip-path="url(#cover${i})"/><text x="90" y="${y + 22}" class="ink" font-size="14" font-weight="600">${esc(shorten(track.name, 15))}</text><text x="90" y="${y + 42}" class="muted" font-size="11">${esc(shorten(track.artists.map(a => a.name).join(' · '), 23))}</text></g>`
  }).join('')
  const empty = '<text x="160" y="245" text-anchor="middle" class="muted" font-size="14">No listening history this week</text>'
  return frame('NetEase Cloud Music — weekly listening', `${heading('This week', 'NetEase Cloud Music')}${logo}${tracks.length ? rows : empty}`)
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv[2] === 'spotify') await spotify()
    else if (process.argv[2] === 'netease') await netease()
    else throw new Error('Choose spotify or netease')
  } catch (error) {
    // Never log request URLs, payloads, user IDs, or response bodies.
    const safe = error.message.replaceAll(process.env.NETEASE_USER_ID || '\u0000', '[redacted]').replace(/https?:\/\/\S+/g, '[URL]')
    console.error(`Music update failed; previous card preserved. ${safe}`)
    process.exitCode = 1
  }
}
