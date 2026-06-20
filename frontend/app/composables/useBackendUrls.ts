import { resolveApiUrl, resolveWebSocketUrl } from '~/utils/backendUrls'

export function useBackendUrls() {
  return {
    apiUrl: resolveApiUrl(),
    wsUrl: resolveWebSocketUrl(),
  }
}
