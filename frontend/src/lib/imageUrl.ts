const LOCAL_MEDIA_HOSTS = new Set(['localhost', '127.0.0.1'])

export function resolveImageUrl(url?: string | null): string {
  if (typeof url !== 'string' || !url.trim()) return ''

  const candidate = url.trim()
  try {
    const parsedUrl = new URL(candidate)
    const isHttp = parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:'
    const isLocalHost = LOCAL_MEDIA_HOSTS.has(parsedUrl.hostname)
    const isMediaPath = parsedUrl.pathname.startsWith('/media/')

    if (isHttp && isLocalHost && isMediaPath && !parsedUrl.username && !parsedUrl.password) {
      return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`
    }

    return url
  } catch {
    try {
      // Preserve valid relative paths while returning an empty source for malformed URLs.
      new URL(candidate, 'http://relative.invalid')
      return url
    } catch {
      return ''
    }
  }
}
