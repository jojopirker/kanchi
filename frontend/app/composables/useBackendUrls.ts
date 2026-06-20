import { useRuntimeConfig } from '#imports'
import { publicUrlPrefix, resolveApiUrl, resolveWebSocketUrl } from '~/utils/backendUrls'

export function useBackendUrls() {
  const config = useRuntimeConfig()
  const runtimePublic = config.public as Record<string, string | undefined>
  const prefix = publicUrlPrefix(runtimePublic.urlPrefix)

  return {
    apiUrl: resolveApiUrl(runtimePublic.apiUrl, prefix),
    wsUrl: resolveWebSocketUrl(runtimePublic.wsUrl, prefix),
  }
}
