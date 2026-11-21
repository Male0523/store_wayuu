import assert from 'node:assert/strict'
import test from 'node:test'
import { withTimeout, RequestTimeoutError } from '../src/lib/http.ts'

test('aborts a request and its response processing after the configured timeout', async () => {
  const pendingOperation = (signal) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true })
  })
  await assert.rejects(
    withTimeout(pendingOperation, 10),
    RequestTimeoutError,
  )
})

test('preserves caller cancellation without reporting a timeout', async () => {
  const controller = new AbortController()
  const pendingOperation = (signal) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => {
      const error = new Error('aborted')
      error.name = 'AbortError'
      reject(error)
    }, { once: true })
  })
  const request = withTimeout(pendingOperation, 1000, controller.signal)
  controller.abort()
  await assert.rejects(request, { name: 'AbortError' })
})

test('passes existing credentials and request options through to fetch', async () => {
  let received
  const response = new Response('', { status: 200 })
  const fetcher = async (_input, init) => { received = init; return response }
  const actual = await withTimeout((signal) => fetcher('/api/v1/auth/me/', {
    credentials: 'include', headers: { 'X-Test': 'kept' }, signal,
  }), 1000)
  assert.equal(actual, response)
  assert.equal(received.credentials, 'include')
  assert.equal(new Headers(received.headers).get('X-Test'), 'kept')
  assert.ok(received.signal instanceof AbortSignal)
})
