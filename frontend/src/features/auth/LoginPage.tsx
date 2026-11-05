import { useState, type FormEvent } from "react"

import Button from "../../components/ui/Button"

import Card from "../../components/ui/Card"

import { signIn, signUp } from "../../api/auth"

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login")

  const [email, setEmail] = useState("")

  const [password, setPassword] = useState("")

  const [message, setMessage] = useState("")

  const [busy, setBusy] = useState(false)

  const register = mode === "register"

  async function submit(event: FormEvent) {
    event.preventDefault()

    if (busy) return

    setBusy(true)

    setMessage("")

    try {
      if (register) {
        const result = await signUp(email.trim(), password)

        if (result.message) setMessage(result.message)
        else if (result.needsConfirmation)
          setMessage("Hãy mở email để xác nhận tài khoản, rồi đăng nhập.")
      } else {
        setMessage(await signIn(email.trim(), password))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-page" id="main-content">
      <img
        className="auth-logo"
        src="/brand/logo-horizontal-light-transparent.png"
        alt="StudyFlow AI"
        width={1840}
        height={366}
      />
      <Card
        className="auth-card"
        title={register ? "Tạo tài khoản" : "Đăng nhập"}
      >
        <form className="auth-form" onSubmit={submit} noValidate={false}>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Mật khẩu
            <input
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={register ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {message && (
            <p className="auth-message" role="alert">
              {message}
            </p>
          )}
          <Button className="primary" type="submit" disabled={busy}>
            {busy ? "Đang xử lý..." : register ? "Tạo tài khoản" : "Đăng nhập"}
          </Button>
          <Button
            className="secondary"
            onClick={() => {
              setMode(register ? "login" : "register")

              setMessage("")
            }}
          >
            {register
              ? "Đã có tài khoản? Đăng nhập"
              : "Chưa có tài khoản? Đăng ký"}
          </Button>
        </form>
      </Card>
    </main>
  )
}
