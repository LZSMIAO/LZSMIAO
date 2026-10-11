import { createHash } from 'node:crypto'
import { requestData } from './music_request.mjs'

export const coverKey = url => createHash('sha256').update(String(url)).digest('hex')
export function coverImage(bytes) {
  const type = bytes[0] === 255 && bytes[1] === 216 ? 'image/jpeg'
    : bytes.subarray(0, 8).toString('hex') === '89504e470d0a1a0a' ? 'image/png'
      : bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP' ? 'image/webp' : null
  if (!type || bytes.length > 2000000) throw new Error('COVER_IMAGE_INVALID')
  return `data:${type};base64,${bytes.toString('base64')}`
}
export async function cachedCover(url, cache, dependencies = {}) {
  const key = coverKey(url)
  const saved = cache[key]
  // Only reuse a validated image for the exact same URL, never another song's cover.
  if (typeof saved === 'string' && saved.length <= 2700000) {
    const match = saved.match(/^data:image\/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$/)
    if (match) {
      try {
        if (coverImage(Buffer.from(match[1], 'base64')) === saved) return saved
      } catch {}
    }
  }
  return coverImage(await requestData(url, {}, 'bytes', 'cover image', dependencies))
}
