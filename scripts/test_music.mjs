import { test } from 'node:test'
import assert from 'node:assert/strict'
import { offlineCard, songLinks } from './update_music.mjs'
test('offline card matches music dimensions and has no fake animation', () => {
  const svg = offlineCard('data:image/png;base64,AAAA')
  assert.match(svg, /width="320" height="445"/)
  assert.match(svg, /rx="10" fill="#121212"/)
  assert.match(svg, /Not playing/)
  assert.doesNotMatch(svg, /animation|<animate|Recently played|<script/)
})
test('song and artist links are independent and escaped', () => {
  const html = songLinks([{ id: '123', name: '<Hello & world>', artists: [{id: '456', name: 'A & B'}]}])
  assert.match(html, /song\?id=123/)
  assert.match(html, /artist\?id=456/)
  assert.match(html, /&lt;Hello &amp; world&gt;/)
  assert.doesNotMatch(html, /user\/home|<table|<Hello/)
})
