import { test } from 'node:test'
import assert from 'node:assert/strict'
import { offlineCard } from './update_music.mjs'
test('offline card matches music dimensions and has no fake animation', () => {
  const svg = offlineCard('data:image/png;base64,AAAA')
  assert.match(svg, /width="320" height="445"/)
  assert.match(svg, /rx="10" fill="#121212"/)
  assert.match(svg, /Not playing/)
  assert.doesNotMatch(svg, /animation|<animate|Recently played|<script/)
})
