import { createApiClient } from "./client"

import { apiConfig } from "./config"

import { getAccessToken, signOut } from "./auth"

import { createEndpoints } from "./endpoints"

// Shared client for the screens. A 401 means the token is no longer valid, so the session is ended.
export const api = createEndpoints(
  createApiClient({
    baseUrl: apiConfig.baseUrl,

    getToken: getAccessToken,

    onUnauthenticated: () => void signOut(),
  }),
)
