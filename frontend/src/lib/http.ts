export class RequestTimeoutError extends Error {
  constructor() {
    super('La solicitud tardó demasiado. Intenta de nuevo.')
    this.name = 'RequestTimeoutError'
  }
}

export async function withTimeout<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  timeoutMs = 15000,
  originalSignal?: AbortSignal | null,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const abortFromCaller = () => controller.abort(originalSignal?.reason)

  if (originalSignal?.aborted) abortFromCaller()
  else originalSignal?.addEventListener('abort', abortFromCaller, { once: true })

  const timeout = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    return await operation(controller.signal)
  } catch (error) {
    if (timedOut) throw new RequestTimeoutError()
    throw error
  } finally {
    clearTimeout(timeout)
    originalSignal?.removeEventListener('abort', abortFromCaller)
  }
}
