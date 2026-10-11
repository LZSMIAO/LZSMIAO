import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cachedCover, coverImage, coverKey } from './music_cover.mjs'
const url = 'https://p1.music.126.net/album.jpg?param=160y160'
const png = Buffer.from('89504e470d0a1a0a', 'hex')
const image = coverImage(png)

test('validated exact cover cache avoids the network, even when source is down', async () => {
  assert.equal(await cachedCover(url, { [coverKey(url)]: image }, {
    fetch: async () => assert.fail('cache should avoid network'),
  }), image)
})
test('different album URLs never reuse another cover', async () => {
  let calls = 0
  await assert.rejects(cachedCover(url + 'x', { [coverKey(url)]: image }, {
    fetch: async () => { calls++; throw new TypeError('fetch failed') }, sleep: async () => {},
  }), /attempts=3/)
  assert.equal(calls, 3)
})
test('corrupt cache is replaced with validated fetched bytes', async () => {
  assert.equal(await cachedCover(url, { [coverKey(url)]: 'data:image/png;base64,AAAA' }, {
    fetch: async () => ({ ok: true, arrayBuffer: async () => png }),
  }), image)
})
test('invalid and oversized images are rejected', () => {
  assert.throws(() => coverImage(Buffer.from('not an image')), /COVER_IMAGE_INVALID/)
  assert.throws(() => coverImage(Buffer.concat([png, Buffer.alloc(2000000)])), /COVER_IMAGE_INVALID/)
})
