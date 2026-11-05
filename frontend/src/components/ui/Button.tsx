import type { ButtonHTMLAttributes } from "react"

export default function Button({
  className = "",

  children,

  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={`button ${className}`} {...props}>
      {children}
    </button>
  )
}
