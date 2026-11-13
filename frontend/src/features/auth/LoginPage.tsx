import { useState, type FormEvent } from "react"
import { AlertCircle, Eye, EyeOff, Lock, Mail } from "lucide-react"

import Button from "../../components/ui/Button"
import { signIn, signUp } from "../../api/auth"

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)

  const register = mode === "register"

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return

    if (register) {
      if (password.length < 8) {
        setMessage("Mật khẩu phải có ít nhất 8 ký tự.")
        return
      }
      if (password !== confirmPassword) {
        setMessage("Mật khẩu nhập lại không khớp.")
        return
      }
    }

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
      <div className="auth-brand-wrap">
        <img
          className="auth-logo"
          src="/brand/logo-horizontal-light-transparent.png"
          alt="StudyFlow AI"
          width={1840}
          height={366}
        />
      </div>

      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-title">
            {register ? "Tạo tài khoản" : "Đăng nhập"}
          </h1>
          <p className="auth-subtitle">
            {register
              ? "Bắt đầu hành trình học tập thông minh cùng StudyFlow AI"
              : "Chào mừng bạn quay lại với StudyFlow AI"}
          </p>
        </div>

        <form className="auth-form" onSubmit={submit} noValidate={false}>
          <div className="auth-field">
            <label htmlFor="auth-email">Email</label>
            <div className="auth-input-wrap">
              <Mail size={17} className="auth-input-icon" aria-hidden="true" />
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="auth-field">
            <label htmlFor="auth-password">Mật khẩu</label>
            <div className="auth-input-wrap">
              <Lock size={17} className="auth-input-icon" aria-hidden="true" />
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 8 : undefined}
                placeholder={register ? "Tối thiểu 8 ký tự" : "••••••••"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {register && (
              <span className="auth-field-hint">Dùng ít nhất 8 ký tự.</span>
            )}
          </div>

          {register && (
            <div className="auth-field">
              <label htmlFor="auth-confirm-password">Nhập lại mật khẩu</label>
              <div className="auth-input-wrap">
                <Lock
                  size={17}
                  className="auth-input-icon"
                  aria-hidden="true"
                />
                <input
                  id="auth-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="Nhập lại mật khẩu"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={
                    showConfirmPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"
                  }
                  title={showConfirmPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  tabIndex={-1}
                >
                  {showConfirmPassword ? (
                    <EyeOff size={16} />
                  ) : (
                    <Eye size={16} />
                  )}
                </button>
              </div>
            </div>
          )}

          {message && (
            <div className="auth-message" role="alert">
              <AlertCircle
                size={16}
                className="auth-message-icon"
                aria-hidden="true"
              />
              <span>{message}</span>
            </div>
          )}

          <Button
            className="primary auth-submit-btn"
            type="submit"
            disabled={busy}
          >
            {busy ? "Đang xử lý..." : register ? "Tạo tài khoản" : "Đăng nhập"}
          </Button>

          <div className="auth-switch">
            <span>{register ? "Đã có tài khoản?" : "Chưa có tài khoản?"}</span>
            <button
              type="button"
              className="auth-switch-btn"
              onClick={() => {
                setMode(register ? "login" : "register")
                setMessage("")
                setConfirmPassword("")
              }}
            >
              {register ? "Đăng nhập ngay" : "Đăng ký ngay"}
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}
