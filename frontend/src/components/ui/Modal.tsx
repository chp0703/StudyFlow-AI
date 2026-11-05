import { useEffect, useId, useRef, type ReactNode } from "react"

import { X } from "lucide-react"

import Button from "./Button"

export default function Modal({
  title,

  close,

  children,
}: {
  title: string

  close: () => void

  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)

  const headingId = useId()

  useEffect(() => {
    const dialog = ref.current

    const previous = document.activeElement as HTMLElement | null

    const overflow = document.body.style.overflow

    dialog?.showModal()

    document.body.style.overflow = "hidden"

    return () => {
      dialog?.close()

      document.body.style.overflow = overflow

      if (previous?.isConnected) previous.focus()
    }
  }, [])

  return (
    <dialog
      ref={ref}
      className="modal-frame"
      aria-labelledby={headingId}
      onCancel={(event) => {
        event.preventDefault()

        close()
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) close()
      }}
    >
      <div className="modal">
        <div className="modal-heading">
          <h2 id={headingId}>{title}</h2>
          <Button
            className="icon-button"
            onClick={close}
            aria-label="Đóng hộp thoại"
          >
            <X aria-hidden="true" size={20} />
          </Button>
        </div>
        {children}
      </div>
    </dialog>
  )
}
