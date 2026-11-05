import { useEffect, useRef, useState } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import {
  Bell,
  BookOpen,
  CalendarDays,
  ChevronDown,
  Check,
  House,
  Settings,
  X,
} from "lucide-react"

import Button from "./components/ui/Button"

import HomeSummary from "./components/HomeSummary"

import Modal from "./components/ui/Modal"

import Assistant from "./features/assistant/Assistant"

import Planner from "./pages/Planner"

import Study from "./pages/Study"

import type { Task } from "./types/task"

const destinations = [
  { name: "Assistant", label: "Trang chủ", icon: House },

  { name: "Planner", label: "Lập kế hoạch", icon: CalendarDays },

  { name: "Study", label: "Học tập", icon: BookOpen },
]

type PageInfo = {
  title: string

  description?: string
}

const pageInfo: Record<string, PageInfo> = {
  Planner: {
    title: "Lập kế hoạch",
  },

  Study: {
    title: "Học tập",
  },
}

type ModalInfo = {
  title: string

  text: string
}

const infoModals: Record<string, ModalInfo> = {
  notifications: { title: "Thông báo của bạn", text: "Chưa có thông báo nào." },

  account: { title: "Tài khoản", text: "Chưa kết nối tài khoản." },

  settings: { title: "Cài đặt", text: "Chưa có cài đặt nào." },

  help: { title: "Trợ giúp & phản hồi", text: "Chưa có nội dung trợ giúp." },
}

export default function App() {
  const [page, setPage] = useState("Assistant")

  const [tasks, setTasks] = useState<Task[]>([])

  const [modal, setModal] = useState("")

  const [notice, setNotice] = useState("")

  const mainHeadingRef = useRef<HTMLHeadingElement>(null)

  const mainRef = useRef<HTMLElement>(null)

  const firstPage = useRef(true)

  // Cards slide up each time a page opens.

  useGSAP(
    () => {
      const cards = gsap.utils

        .toArray<HTMLElement>(".card, .assistant-shell")

        .filter((el) => el.offsetParent !== null)

      gsap.from(cards, {
        y: 48,

        opacity: 0,

        duration: 0.5,

        ease: "power2.out",

        stagger: 0.08,

        clearProps: "transform,opacity",
      })
    },

    { scope: mainRef, dependencies: [page] },
  )

  useEffect(() => {
    document.documentElement.lang = "vi"
  }, [])

  useEffect(() => {
    document.title = `${
      destinations.find((d) => d.name === page)?.label ?? page
    } | StudyFlow AI`

    if (firstPage.current) {
      firstPage.current = false

      return
    }

    if (page === "Assistant")
      document.querySelector<HTMLElement>("[data-assistant-heading]")?.focus()
    else mainHeadingRef.current?.focus()

    window.scrollTo({ top: 0, behavior: "instant" })
  }, [page])

  const go = (p: string) => {
    setPage(p)
  }

  const info = pageInfo[page]

  const infoModal = infoModals[modal]

  return (
    <div className={`app-shell ${page === "Assistant" ? "assistant-app" : ""}`}>
      <a className="skip-link" href="#main-content">
        Bỏ qua đến nội dung chính
      </a>
      <header className="topbar">
        <div className="brand">
          <img
            className="brand-logo"
            src="/brand/logo-horizontal-light-transparent.png"
            alt="StudyFlow AI"
            width={1840}
            height={366}
            fetchPriority="high"
          />
        </div>
        <div className="top-actions">
          <Button
            className="icon-button notification"
            aria-label="Thông báo"
            onClick={() => setModal("notifications")}
          >
            <Bell aria-hidden="true" size={17} />
            <i />
          </Button>
          <span className="top-divider" />
          <Button
            className="profile"
            aria-label="Tài khoản sinh viên"
            onClick={() => setModal("account")}
          >
            <span className="avatar">S</span>
            <span>Sinh viên</span>
            <ChevronDown aria-hidden="true" size={13} />
          </Button>
        </div>
      </header>
      <aside className="sidebar">
        <nav aria-label="Điều hướng chính">
          {destinations.map((n) => (
            <Button
              key={n.name}
              className={`nav-item ${page === n.name ? "active" : ""}`}
              aria-label={n.label}
              aria-current={page === n.name ? "page" : undefined}
              onClick={() => go(n.name)}
            >
              <n.icon size={18} />
              <span>{n.label}</span>
              {page === n.name && <i />}
            </Button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Button
            className="nav-item"
            aria-label="Cài đặt"
            onClick={() => setModal("settings")}
          >
            <Settings aria-hidden="true" size={18} />
            <span>Cài đặt</span>
          </Button>
        </div>
      </aside>
      <main
        ref={mainRef}
        className={`main-content ${page === "Assistant" ? "home-content" : ""}`}
        id="main-content"
        tabIndex={-1}
      >
        {info && (
          <div className="page-heading">
            <div>
              <h1 ref={mainHeadingRef} tabIndex={-1}>
                {info.title}
              </h1>
              {info.description && <p>{info.description}</p>}
            </div>
          </div>
        )}
        <div className="home-layout" hidden={page !== "Assistant"}>
          <Assistant onOpenPlanner={() => go("Planner")} />
          <aside className="home-summary" aria-label="Tổng quan việc học">
            <HomeSummary tasks={tasks} go={go} />
          </aside>
        </div>
        {page === "Planner" && (
          <Planner tasks={tasks} setTasks={setTasks} notify={setNotice} />
        )}
        <div
          hidden={page !== "Study"}
          className={page === "Study" ? "study-page-wrapper" : ""}
        >
          <Study />
        </div>
      </main>
      {infoModal && (
        <Modal title={infoModal.title} close={() => setModal("")}>
          <p>{infoModal.text}</p>
          <Button className="secondary" onClick={() => setModal("")}>
            Đã hiểu
          </Button>
        </Modal>
      )}
      {notice && (
        <div className="toast">
          <span role="status">{notice}</span>
          <Check aria-hidden="true" size={17} />
          <Button
            className="icon-button"
            aria-label="Đóng thông báo"
            onClick={() => setNotice("")}
          >
            <X aria-hidden="true" size={14} />
          </Button>
        </div>
      )}
    </div>
  )
}
