interface RuntimeBackendUrls {
  apiUrl?: string
  wsUrl?: string
  frontendUrl?: string
  urlPrefix?: string
}

declare global {
  interface Window {
    __KANCHI_BACKEND_URLS__?: RuntimeBackendUrls
  }
}

function runtimeUrls(): RuntimeBackendUrls {
  if (typeof window === 'undefined') {
    return {}
  }
  return window.__KANCHI_BACKEND_URLS__ || {}
}

function normalizePrefix(prefix: string | undefined): string {
  const value = prefix?.trim()
  if (!value) {
    return ''
  }

  const normalized = `/${value.replace(/^\/+|\/+$/g, '')}`
  return normalized === '/' ? '' : normalized
}

function withPrefix(path: string, prefix: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!prefix || normalizedPath === prefix || normalizedPath.startsWith(`${prefix}/`)) {
    return normalizedPath
  }
  return `${prefix}${normalizedPath}`
}

function isAbsoluteUrl(url: string): boolean {
  return /^[a-z][a-z\d+\-.]*:\/\//i.test(url)
}

function withUrlPrefix(url: string, prefix: string): string {
  if (!prefix) {
    return url
  }
  if (!isAbsoluteUrl(url)) {
    return withPrefix(url, prefix)
  }

  const parsed = new URL(url)
  parsed.pathname = withPrefix(parsed.pathname, prefix)
  return parsed.toString().replace(/\/$/, '')
}

function joinPath(base: string, path: string): string {
  if (!path) {
    return base || '/'
  }
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`
}

export function useBackendUrls() {
  const config = runtimeUrls()
  const prefix = normalizePrefix(config.urlPrefix)
  const apiUrl = config.apiUrl ? withUrlPrefix(config.apiUrl, prefix) : prefix
  const wsUrl = withUrlPrefix(config.wsUrl || '/ws', prefix)
  const frontendBaseUrl = withUrlPrefix(config.frontendUrl || '/ui', prefix)

  return {
    apiUrl,
    wsUrl,
    frontendUrl: (path: string) => joinPath(frontendBaseUrl, path),
  }
}
