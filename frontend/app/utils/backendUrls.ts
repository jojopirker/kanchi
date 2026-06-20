function browserPathname(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.location.pathname
}

export function normalizePrefix(prefix: string | undefined): string {
  const value = prefix?.trim()
  if (!value) {
    return ''
  }

  const normalized = `/${value.replace(/^\/+|\/+$/g, '')}`
  return normalized === '/' ? '' : normalized
}

export function pathWithPrefix(path: string, prefix: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!prefix || normalizedPath === prefix || normalizedPath.startsWith(`${prefix}/`)) {
    return normalizedPath
  }

  return `${prefix}${normalizedPath}`
}

export function isAbsoluteUrl(url: string): boolean {
  return /^[a-z][a-z\d+\-.]*:\/\//i.test(url)
}

export function browserPathPrefix(pathname = browserPathname()): string {
  const match = pathname.match(/^(.*)\/ui(?:\/|$)/)
  if (!match?.[1]) {
    return ''
  }

  return normalizePrefix(match[1])
}

export function publicUrlPrefix(configPrefix?: string): string {
  return normalizePrefix(configPrefix) || browserPathPrefix()
}

export function resolveApiUrl(configuredApiUrl?: string, prefix = publicUrlPrefix()): string {
  if (!configuredApiUrl) {
    if (typeof window === 'undefined') {
      return 'http://localhost:8765'
    }
    return prefix
  }

  const trimmed = configuredApiUrl.replace(/\/+$/, '')
  return isAbsoluteUrl(trimmed) ? trimmed : pathWithPrefix(trimmed, prefix)
}

export function resolveWebSocketUrl(configuredWsUrl?: string, prefix = publicUrlPrefix()): string {
  if (configuredWsUrl) {
    return isAbsoluteUrl(configuredWsUrl) ? configuredWsUrl : pathWithPrefix(configuredWsUrl, prefix)
  }

  if (typeof window === 'undefined') {
    return 'ws://localhost:8765/ws'
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${prefix}/ws`
}

export function resolveFrontendUrl(path: string, prefix = publicUrlPrefix()): string {
  const publicPath = pathWithPrefix(path, prefix)
  if (typeof window === 'undefined') {
    return publicPath
  }

  return new URL(publicPath, window.location.origin).toString()
}
