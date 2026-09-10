import { createCipheriv, createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

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
function frame(title, content) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="445" viewBox="0 0 320 445" role="img" aria-label="${esc(title)}"><style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC",sans-serif}</style><rect width="320" height="445" rx="10" fill="#121212"/>${content}</svg>`
}
export function offlineCard(logo) {
  return frame('Spotify — not playing', `<text x="20" y="36" fill="#f0f6fc" font-size="17" font-weight="600">Spotify</text><image x="275" y="20" width="25" height="25" href="${logo}"/><circle cx="160" cy="185" r="42" fill="#1c1c1c"/><image x="139" y="164" width="42" height="42" opacity="0.55" href="${logo}"/><text x="160" y="267" text-anchor="middle" fill="#f0f6fc" font-size="23" font-weight="600">Not playing</text><text x="160" y="293" text-anchor="middle" fill="#a7a7a7" font-size="12">Nothing playing right now</text>`)
}
export function songLinks(tracks) {
  return tracks.map(({ id, name, artists }) => `<p><a href="https://music.163.com/song?id=${id}"><strong>${esc(name)}</strong></a> &nbsp;—&nbsp; <small>${artists.map(a => `<a href="https://music.163.com/artist?id=${a.id}">${esc(a.name)}</a>`).join(' · ')}</small></p>`).join('\n')
}
async function publishCard(platform, svg, transform = value => value) {
  const filename = `assets/${platform}-${createHash('sha256').update(svg).digest('hex').slice(0, 12)}.svg`
  let content = await read('README.md')
  const pattern = platform === 'spotify'
    ? /(<img alt="Spotify now playing" src=")[^"]+(" width="49\.5%">)/
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
    const artists = song.ar.map(a => ({ id: String(a.id), name: a.name }))
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
    return { id, name: song.name, artists, image }
  }))
  const previous = await read('assets/netease-clean.svg')
  const logo = previous.match(/<g transform="translate\(275 23\)">.*?<\/g>/)?.[0]
  if (!logo) throw new Error('Existing NetEase logo missing')
  const rows = tracks.map((track, i) => {
    const y = 80 + i * 70
    return `<g><clipPath id="cover${i}"><rect x="20" y="${y}" width="56" height="56" rx="5"/></clipPath><image x="20" y="${y}" width="56" height="56" href="${track.image}" preserveAspectRatio="xMidYMid meet" clip-path="url(#cover${i})"/><text x="90" y="${y + 20}" fill="#f0f6fc" font-size="14" font-weight="600">${esc(shorten(track.name, 15))}</text><text x="90" y="${y + 40}" fill="#a7a7a7" font-size="10.5">${esc(shorten(track.artists.map(a => a.name).join(' · '), 23))}</text></g>`
  }).join('')
  const empty = '<text x="160" y="245" text-anchor="middle" fill="#a7a7a7" font-size="14">No listening history this week</text>'
  const svg = frame('NetEase Cloud Music — weekly listening', `<text x="20" y="34" fill="#f0f6fc" font-size="17" font-weight="600">This week</text><text x="20" y="54" fill="#a7a7a7" font-size="11">NetEase Cloud Music</text>${logo}${tracks.length ? rows : empty}`)
  await publishCard('netease', svg, content => {
    const pattern = /(<a name="music-links"><\/a>\s*<details>\s*<summary>.*?<\/summary>)[\s\S]*?(<\/details>)/
    if (!pattern.test(content)) throw new Error('Song links section missing')
    return content.replace(pattern, (_, start, end) => `${start}\n\n<br>\n\n${songLinks(tracks)}\n\n${end}`)
  })
  console.log(`NetEase: updated ${tracks.length} tracks and matching song links.`)
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
