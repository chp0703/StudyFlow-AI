// API mode needs all three variables; without them the app runs as the local demo (no login, no server).
const env = import.meta.env

export const apiConfig = {
  baseUrl: (env.VITE_API_BASE_URL as string | undefined ?? "").replace(
    /\/$/,
    "",
  ),

  supabaseUrl: env.VITE_SUPABASE_URL as string | undefined ?? "",

  supabaseKey: env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined ?? "",
}

export const apiEnabled = Boolean(
  apiConfig.baseUrl && apiConfig.supabaseUrl && apiConfig.supabaseKey,
)
