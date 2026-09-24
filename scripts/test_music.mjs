import { test } from 'node:test'
import assert from 'node:assert/strict'
import { offlineCard, neteaseCard, weekFile } from './update_music.mjs'
test('offline card matches music dimensions and has no fake animation', () => {
  const svg = offlineCard('data:image/png;base64,AAAA')
  assert.match(svg, /width="320" height="445"/)
  assert.match(svg, /class="bg" width="320" height="445" rx="10"/)
  // Follows the page theme instead of a fixed Spotify black.
  assert.doesNotMatch(svg, /#121212/)
  assert.match(svg, /prefers-color-scheme:dark/)
  assert.match(svg, /Not playing/)
  assert.doesNotMatch(svg, /animation|<animate|Recently played|<script/)
})
test('weekly card follows the reader colour scheme and escapes track names', () => {
  const tracks = [{ id: '1', name: '<b>歌</b>', artists: [{ id: '2', name: '人' }], image: 'data:image/png;base64,AAAA' }]
  const svg = neteaseCard(tracks, '<g transform="translate(275 23)"></g>')
  assert.match(svg, /class="ink serif" font-size="17.5">This week</)
  assert.match(svg, /prefers-color-scheme:dark/)
  assert.doesNotMatch(svg, /#121212|#a7a7a7|<b>/)
  assert.match(svg, /&lt;b&gt;歌&lt;\/b&gt;/)
})
test('the week file carries songs for the linked page and nothing private', () => {
  const tracks = [{ id: '1', name: '歌', artists: [{ id: '2', name: '人' }], image: 'data:image/png;base64,AAAA', cover: 'https://p1.music.126.net/a.jpg?param=160y160' }]
  const week = JSON.parse(weekFile(tracks))
  assert.deepEqual(week, { tracks: [{ id: '1', name: '歌', artists: [{ id: '2', name: '人' }], cover: 'https://p1.music.126.net/a.jpg?param=160y160' }] })
  assert.doesNotMatch(weekFile(tracks), /base64|uid|NETEASE/)
})
