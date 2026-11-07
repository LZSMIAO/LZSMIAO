import { test } from 'node:test'
import assert from 'node:assert/strict'
import { requestData, validateWeekly, weeklyRetryDelays } from './music_request.mjs'

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

test('business failures retry inside HTTP 200 and recover', async () => {
  let calls = 0
  const value = await requestData('private', {}, 'json', 'weekly history', {
    fetch: async () => ({ ok: true, json: async () => ++calls === 1 ? { code: 503 } : calls === 2 ? { code: 200 } : { code: 200, weekData: [] } }),
    sleep: async () => {}, validate: validateWeekly,
  })
  assert.equal(calls, 3)
  assert.deepEqual(value.weekData, [])
})
test('business authentication failures do not retry or leak response details', async () => {
  await assert.rejects(requestData('private', {}, 'json', 'weekly history', {
    fetch: async () => ({ ok: true, json: async () => ({ code: 403, message: 'private ID and payload' }) }),
    sleep: async () => assert.fail('unexpected retry'), validate: validateWeekly,
  }), { message: 'weekly history request failed (BUSINESS_403; attempts=1)' })
})
test('missing weekly data exhausts bounded retries; invalid codes cannot leak IDs', async () => {
  let calls = 0
  await assert.rejects(requestData('private', {}, 'json', 'weekly history', {
    fetch: async () => { calls++; return { ok: true, json: async () => ({ code: 200 }) } },
    sleep: async () => {}, validate: validateWeekly,
  }), { message: 'weekly history request failed (WEEK_DATA_MISSING; attempts=3)' })
  assert.equal(calls, 3)
  assert.equal(validateWeekly({ code: 123456789 }).reason, 'BUSINESS_CODE_INVALID')
  assert.equal(validateWeekly(null).reason, 'RESPONSE_NULL')
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


test('weekly retries span an upstream disturbance and recover on fourth attempt', async () => {
  let calls = 0
  const waits = []
  const value = await requestData('private', {}, 'json', 'weekly history', {
    fetch: async () => ({ ok: true, json: async () => ++calls < 4 ? {} : { code: 200, weekData: [] } }),
    sleep: async ms => waits.push(ms), validate: validateWeekly, retryDelays: weeklyRetryDelays,
  })
  assert.equal(calls, 4)
  assert.deepEqual(waits, [2000, 8000, 20000])
  assert.deepEqual(value, { code: 200, weekData: [] })
})
test('weekly exhaustion remains a failure, never stale success', async () => {
  let calls = 0
  await assert.rejects(requestData('private', {}, 'json', 'weekly history', {
    fetch: async () => { calls++; return { ok: true, json: async () => ({ message: 'private user payload' }) } },
    sleep: async () => {}, validate: validateWeekly, retryDelays: weeklyRetryDelays,
  }), { message: 'weekly history request failed (BUSINESS_CODE_MISSING; attempts=4)' })
  assert.equal(calls, 4)
})
test('invalid response diagnostics never interpolate upstream values', () => {
  for (const [input, reason] of [
    [null, 'RESPONSE_NULL'], [[], 'RESPONSE_ARRAY'], ['secret', 'RESPONSE_NOT_OBJECT'],
    [{}, 'BUSINESS_CODE_MISSING'], [{ code: 'secret-id' }, 'BUSINESS_CODE_STRING'],
    [{ code: 123456789 }, 'BUSINESS_CODE_INVALID'], [{ code: -462 }, 'BUSINESS_NEGATIVE_462'],
  ]) assert.equal(validateWeekly(input).reason, reason)
  assert.notEqual(validateWeekly({ code: '200', weekData: [] }), null)
})
test('explicit nonstandard rejection codes stop without blind retries', async () => {
  for (const code of [-460, -462]) {
    assert.equal(validateWeekly({ code }).retryable, false)
    await assert.rejects(requestData('private', {}, 'json', 'weekly history', {
      fetch: async () => ({ ok: true, json: async () => ({ code, message: 'private' }) }),
      sleep: async () => assert.fail('unexpected retry'), validate: validateWeekly, retryDelays: weeklyRetryDelays,
    }), /BUSINESS_NEGATIVE_(460|462); attempts=1/)
  }
})
test('retry policies cannot create unbounded work', async () => {
  for (const retryDelays of [[1,2,3,4], [Infinity], [-1], [30001]]) {
    await assert.rejects(requestData('private', {}, 'json', 'weekly history', {
      fetch: async () => assert.fail('unexpected request'), retryDelays,
    }), { message: 'INVALID_RETRY_POLICY' })
  }
})
