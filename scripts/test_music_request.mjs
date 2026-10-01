import { test } from 'node:test'
import assert from 'node:assert/strict'
import { requestData } from './music_request.mjs'

test('retries transient connection and body failures with bounded backoff', async () => {
  let calls = 0
  const waits = []
  const result = await requestData('https://example.invalid/secret', {}, 'json', 'weekly history', {
    fetch: async () => {
      calls++
      if (calls === 1) throw new TypeError('fetch failed', { cause: { code: 'ECONNRESET' } })
      if (calls === 2) return { ok: true, json: async () => { throw Object.assign(new Error('private body'), { code: 'UND_ERR_SOCKET' }) } }
      return { ok: true, json: async () => ({ weekData: [] }) }
    },
    sleep: async ms => waits.push(ms),
  })
  assert.deepEqual(result, { weekData: [] })
  assert.equal(calls, 3)
  assert.deepEqual(waits, [1000, 2000])
})
test('exhausted retries expose only stage and safe code', async () => {
  let calls = 0
  await assert.rejects(requestData('private URL', {}, 'bytes', 'cover image', {
    fetch: async () => { calls++; throw new TypeError('fetch failed', { cause: { code: 'ETIMEDOUT', message: 'private' } }) },
    sleep: async () => {},
  }), { message: 'cover image request failed (ETIMEDOUT; attempts=3)' })
  assert.equal(calls, 3)
})
test('HTTP authentication errors and invalid JSON do not retry', async () => {
  for (const response of [
    { ok: false, status: 403, body: { cancel: async () => {} } },
    { ok: true, json: async () => { throw new SyntaxError('private payload') } },
  ]) {
    let calls = 0
    await assert.rejects(requestData('private URL', {}, 'json', 'weekly history', {
      fetch: async () => { calls++; return response }, sleep: async () => assert.fail('unexpected retry'),
    }), /weekly history request failed \((HTTP_403|INVALID_JSON); attempts=1\)/)
    assert.equal(calls, 1)
  }
})
test('retries 429 and 503 and consumes binary body', async () => {
  let calls = 0
  const bytes = await requestData('private URL', {}, 'bytes', 'cover image', {
    fetch: async () => ++calls < 3
      ? { ok: false, status: calls === 1 ? 429 : 503, body: { cancel: async () => {} } }
      : { ok: true, arrayBuffer: async () => new Uint8Array([255, 216]).buffer },
    sleep: async () => {},
  })
  assert.deepEqual([...bytes], [255, 216])
})
