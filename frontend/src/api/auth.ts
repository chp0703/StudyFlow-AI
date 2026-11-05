import { useEffect, useState } from "react"

import { createClient, type Session } from "@supabase/supabase-js"

import { apiConfig, apiEnabled } from "./config"

// supabase-js keeps the session in the browser's localStorage; the app never touches the token itself.
const supabase = apiEnabled
  ? createClient(apiConfig.supabaseUrl, apiConfig.supabaseKey)
  : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null

  const { data } = await supabase.auth.getSession()

  return data.session?.access_token ?? null
}

const LOGIN_ERRORS: Record<string, string> = {
  invalid_credentials: "Email hoặc mật khẩu không đúng.",

  user_already_exists: "Email này đã có tài khoản. Hãy đăng nhập.",

  weak_password: "Mật khẩu quá yếu. Hãy dùng ít nhất 8 ký tự.",

  over_request_rate_limit: "Thao tác quá nhanh. Hãy thử lại sau ít phút.",

  email_not_confirmed: "Hãy xác nhận email trước khi đăng nhập.",
}

type AuthFailure = {
  code?: string

  message?: string
}

const fail = (error: AuthFailure) =>
  LOGIN_ERRORS[error.code ?? ""] ?? "Không thực hiện được. Hãy thử lại."

// Returns an error message, or "" on success. `needsConfirmation` means an email must be confirmed first.
export async function signIn(email: string, password: string) {
  if (!supabase) return "Chưa cấu hình đăng nhập."

  const { error } = await supabase.auth.signInWithPassword({ email, password })

  return error ? fail(error) : ""
}

export async function signUp(email: string, password: string) {
  if (!supabase)
    return { message: "Chưa cấu hình đăng nhập.", needsConfirmation: false }

  const { data, error } = await supabase.auth.signUp({ email, password })

  if (error) return { message: fail(error), needsConfirmation: false }

  return { message: "", needsConfirmation: !data.session }
}

export async function signOut() {
  await supabase?.auth.signOut()
}

export type SessionState = {
  session: Session | null

  loading: boolean
}

export function useSession(): SessionState {
  const [session, setSession] = useState<Session | null>(null)

  const [loading, setLoading] = useState(Boolean(supabase))

  useEffect(() => {
    if (!supabase) return

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)

      setLoading(false)
    })

    const { data } = supabase.auth.onAuthStateChange((_event, next) =>
      setSession(next),
    )

    return () => data.subscription.unsubscribe()
  }, [])

  return { session, loading }
}
