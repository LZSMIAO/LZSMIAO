import { setTimeout as delay } from 'node:timers/promises'

// Four weekly attempts span short upstream disturbances without hammering it.
export const weeklyRetryDelays = Object.freeze([2000, 8000, 20000])

const retryCodes = new Set(['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_BODY_TIMEOUT', 'UND_ERR_SOCKET'])
function codeOf(error) {
  const code = error?.cause?.code || error?.code || error?.name
  return retryCodes.has(code) ? code : error?.name === 'TimeoutError' ? 'TIMEOUT' : error instanceof SyntaxError ? 'INVALID_JSON' : 'NETWORK_ERROR'
}
// Only fixed stage labels and allowlisted codes reach logs, never URLs or payloads.
export async function requestData(url, options, kind, stage, dependencies = {}) {
  const fetcher = dependencies.fetch || fetch
  const sleep = dependencies.sleep || delay
  const retryDelays = dependencies.retryDelays || [1000, 2000]
  if (!Array.isArray(retryDelays) || retryDelays.length > 3 || retryDelays.some(ms => !Number.isFinite(ms) || ms < 0 || ms > 30000)) throw new Error('INVALID_RETRY_POLICY')
  const attempts = retryDelays.length + 1
  for (let attempt = 1; attempt <= attempts; attempt++) {
    let retryable = false
    let reason
    try {
      const response = await fetcher(url, { ...options, signal: AbortSignal.timeout(20000) })
      if (!response.ok) {
        retryable = response.status === 429 || [500, 502, 503, 504].includes(response.status)
        reason = `HTTP_${response.status}`
        await response.body?.cancel()
        throw new Error(reason)
      }
      // Keep body consumption inside the attempt: a connection can fail after headers.
      const value = kind === 'json' ? await response.json() : Buffer.from(await response.arrayBuffer())
      const invalid = dependencies.validate?.(value)
      if (invalid) {
        reason = invalid.reason
        retryable = invalid.retryable
        throw new Error(reason)
      }
      return value
    } catch (error) {
      if (!reason) {
        reason = codeOf(error)
        retryable = error?.name === 'TimeoutError' || retryCodes.has(error?.cause?.code || error?.code) || (error instanceof TypeError && error.message === 'fetch failed')
      }
      if (!retryable || attempt === attempts) throw new Error(`${stage} request failed (${reason}; attempts=${attempt})`)
      await sleep(retryDelays[attempt - 1])
    }
  }
}

function invalidCodeReason(data) {
  // Fixed labels only: never interpolate untrusted codes, fields or messages.
  if (data === null) return 'RESPONSE_NULL'
  if (Array.isArray(data)) return 'RESPONSE_ARRAY'
  if (typeof data !== 'object') return 'RESPONSE_NOT_OBJECT'
  if (!Object.hasOwn(data, 'code')) return 'BUSINESS_CODE_MISSING'
  if (typeof data.code === 'string') return 'BUSINESS_CODE_STRING'
  if (data.code === -460) return 'BUSINESS_NEGATIVE_460'
  if (data.code === -462) return 'BUSINESS_NEGATIVE_462'
  return 'BUSINESS_CODE_INVALID'
}

export function validateWeekly(data) {
  if (data?.code === 200 && Array.isArray(data.weekData)) return null
  const code = Number.isInteger(data?.code) && data.code >= 100 && data.code <= 599 ? data.code : null
  return {
    reason: code === 200 ? 'WEEK_DATA_MISSING' : code === null ? invalidCodeReason(data) : `BUSINESS_${code}`,
    // Stop on these explicit nonstandard rejections rather than retry blindly.
    retryable: ![-460, -462].includes(data?.code) && (code === null || code === 200 || code === 429 || (code >= 500)),
  }
}
