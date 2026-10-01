import { setTimeout as delay } from 'node:timers/promises'

const retryCodes = new Set(['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_BODY_TIMEOUT', 'UND_ERR_SOCKET'])
function codeOf(error) {
  const code = error?.cause?.code || error?.code || error?.name
  return retryCodes.has(code) ? code : error?.name === 'TimeoutError' ? 'TIMEOUT' : error instanceof SyntaxError ? 'INVALID_JSON' : 'NETWORK_ERROR'
}
// Only fixed stage labels and allowlisted codes reach logs, never URLs or payloads.
export async function requestData(url, options, kind, stage, dependencies = {}) {
  const fetcher = dependencies.fetch || fetch
  const sleep = dependencies.sleep || delay
  for (let attempt = 1; attempt <= 3; attempt++) {
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
      return kind === 'json' ? await response.json() : Buffer.from(await response.arrayBuffer())
    } catch (error) {
      if (!reason) {
        reason = codeOf(error)
        retryable = error?.name === 'TimeoutError' || retryCodes.has(error?.cause?.code || error?.code) || (error instanceof TypeError && error.message === 'fetch failed')
      }
      if (!retryable || attempt === 3) throw new Error(`${stage} request failed (${reason}; attempts=${attempt})`)
      await sleep(attempt * 1000)
    }
  }
}
