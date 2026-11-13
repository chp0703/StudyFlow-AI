import { useEffect, useMemo, useRef, useState } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import {
  Bell,
  BookOpen,
  CalendarDays,
  ChevronDown,
  House,
  PanelLeft,
  PanelLeftClose,
  Settings,
  X,
} from "lucide-react"

import Button from "./components/ui/Button"

import HomeSummary from "./components/HomeSummary"

import Modal from "./components/ui/Modal"

import Assistant from "./features/assistant/Assistant"

import Planner from "./pages/Planner"

import LoginPage from "./features/auth/LoginPage"

import { signOut, useSession } from "./api/auth"

import { apiEnabled } from "./api/config"

import { useServerData } from "./api/useServerData"

import { loadPending, plannerConversationId, savePending } from "./api/pending"

import { api } from "./api"

import { proposalFromReply } from "./api/mappers"

import Study from "./pages/Study"

import type { Proposal, TimeWindow } from "./types/planner"

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

    description: "Quản lý công việc và lịch học trong tuần.",
  },

  Study: {
    title: "Học tập",

    description: "Tài liệu học tập, luyện đề và trao đổi cùng trợ lý AI.",
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

  // Demo mode keeps everything in memory; API mode reads it from the server (see api/useServerData).

  const { session, loading: sessionLoading } = useSession()

  const server = useServerData(apiEnabled && !!session)

  const [demoTasks, setTasks] = useState<Task[]>([])

  const [demoAvailability, setAvailability] = useState<TimeWindow[]>([])

  // Thay đổi lịch đang chờ người dùng duyệt và số phiên bản sửa đổi của lịch đã xác nhận.

  const [proposal, setProposal] = useState<Proposal | null>(null)

  const [demoRevision, setRevision] = useState(0)

  const tasks = apiEnabled ? server.tasks : demoTasks

  const availability = apiEnabled ? server.availability : demoAvailability

  const revision = apiEnabled ? server.revision : demoRevision

  const [modal, setModal] = useState("")

  useEffect(() => {
    setModal("")
  }, [session])

  const [notice, setNotice] = useState("")

  useEffect(() => {
    if (!notice) return

    const timer = window.setTimeout(() => setNotice(""), 3500)

    return () => window.clearTimeout(timer)
  }, [notice])

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      const saved = localStorage.getItem("studyflow_sidebar_open")

      return saved !== null ? saved === "true" : true
    } catch {
      return true
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem("studyflow_sidebar_open", String(sidebarOpen))
    } catch {}
  }, [sidebarOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault()

        setSidebarOpen((v) => !v)
      }
    }

    window.addEventListener("keydown", handleKeyDown)

    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const mainHeadingRef = useRef<HTMLHeadingElement>(null)

  const mainRef = useRef<HTMLElement>(null)

  const firstPage = useRef(true)

  // Khi đổi kích thước qua điểm ngắt responsive, bố cục sắp lại; cho các thẻ chuyển vị trí nhẹ nhàng.

  useEffect(() => {
    const queries = [1250, 800, 480].map((w) =>
      window.matchMedia(`(max-width: ${w}px)`),
    )

    const onChange = () => {
      const cards = gsap.utils

        .toArray<HTMLElement>(".card, .assistant-shell")

        .filter((el) => el.offsetParent !== null)

      gsap.from(cards, {
        opacity: 0.4,

        y: 14,

        scale: 0.985,

        duration: 0.45,

        ease: "power2.out",

        stagger: 0.04,

        clearProps: "transform,opacity",
      })
    }

    queries.forEach((q) => q.addEventListener("change", onChange))

    return () =>
      queries.forEach((q) => q.removeEventListener("change", onChange))
  }, [])

  const firstSidebar = useRef(true)

  // Mở menu: các mục lần lượt hiện ra; đóng menu: nút mở và logo hiện lại nhẹ nhàng.

  useGSAP(
    () => {
      if (firstSidebar.current) {
        firstSidebar.current = false

        return
      }

      // GSAP điều khiển hiệu ứng trượt cả khi hệ điều hành tắt chuyển động và CSS transition bị vô hiệu hóa.

      gsap.fromTo(
        ".app-shell",

        { "--sb-offset": sidebarOpen ? "24px" : "220px" },

        {
          "--sb-offset": sidebarOpen ? "220px" : "24px",

          duration: 0.5,

          ease: "power3.inOut",

          clearProps: "--sb-offset",
        },
      )

      gsap.fromTo(
        ".sidebar",

        { x: sidebarOpen ? -208 : 0, autoAlpha: sidebarOpen ? 0 : 1 },

        {
          x: sidebarOpen ? 0 : -208,

          autoAlpha: sidebarOpen ? 1 : 0,

          duration: 0.5,

          ease: "power3.inOut",

          clearProps: "transform,opacity,visibility",
        },
      )

      if (sidebarOpen) {
        gsap.from(".sidebar .nav-item", {
          x: -16,

          opacity: 0,

          duration: 0.4,

          ease: "power2.out",

          stagger: 0.05,

          delay: 0.12,

          clearProps: "transform,opacity",
        })
      } else {
        gsap.from(".sidebar-reveal-btn", {
          scale: 0.4,

          opacity: 0,

          rotate: -90,

          duration: 0.5,

          ease: "back.out(2)",

          delay: 0.15,

          clearProps: "transform,opacity",
        })

        gsap.from(".brand", {
          x: -6,

          duration: 0.45,

          ease: "power2.out",

          clearProps: "transform",
        })
      }
    },

    { dependencies: [sidebarOpen] },
  )

  // Các thẻ trượt lên mỗi lần mở trang.

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

  // After a reload the pending approval is rebuilt by the server from its reference, never from stored content.

  const restoredFor = useRef("")

  useEffect(() => {
    const userId = session?.user.id

    if (
      !apiEnabled ||
      !userId ||
      server.loading ||
      restoredFor.current === userId
    )
      return

    restoredFor.current = userId

    const pending = loadPending(userId)

    if (!pending) return

    api

      .reviewAction(
        pending.conversationId,

        pending.reference.action_id,

        pending.reference.action_version,
      )

      .then((reply) => {
        const next = proposalFromReply(reply, {
          tasks: server.tasks,

          events: server.events,

          availability: server.availability,

          revision: server.revision,
        })

        if (next && reply.action_reference) {
          setProposal(next)

          savePending(userId, {
            conversationId: pending.conversationId,

            reference: reply.action_reference,
          })
        } else savePending(userId, null)
      })

      .catch(() => savePending(userId, null))
  }, [session?.user.id, server])

  const info = pageInfo[page]

  const email = session?.user.email ?? ""

  const conversationId = useMemo(
    () => plannerConversationId(session?.user.id ?? "demo"),

    [session?.user.id],
  )

  if (apiEnabled && sessionLoading) return null

  if (apiEnabled && !session) return <LoginPage />

  const infoModal = infoModals[modal]

  return (
    <div
      className={`app-shell ${page === "Assistant" ? "assistant-app" : ""} ${
        sidebarOpen ? "sidebar-open" : "sidebar-collapsed"
      }`}
    >
      <a className="skip-link" href="#main-content">
        Bỏ qua đến nội dung chính
      </a>
      <header className="topbar">
        <div
          className={`brand-container ${
            !sidebarOpen ? "can-open-sidebar" : ""
          }`}
        >
          <div
            className="brand"
            onClick={() => {
              if (!sidebarOpen) setSidebarOpen(true)
            }}
          >
            <img
              className="brand-logo"
              src="/brand/logo-horizontal-light-transparent.png"
              alt="StudyFlow AI"
              width={1840}
              height={366}
              fetchPriority="high"
            />
          </div>
          {!sidebarOpen && (
            <Button
              className="icon-button sidebar-reveal-btn"
              aria-label="Mở thanh menu"
              title="Mở menu (Ctrl+B)"
              onClick={() => setSidebarOpen(true)}
            >
              <PanelLeft aria-hidden="true" size={17} />
            </Button>
          )}
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
            <span className="avatar">{(email[0] ?? "S").toUpperCase()}</span>
            <span>{apiEnabled ? email.split("@")[0] : "Sinh viên"}</span>
            <ChevronDown aria-hidden="true" size={13} />
          </Button>
        </div>
      </header>
      <aside
        className="sidebar"
        aria-hidden={!sidebarOpen}
        tabIndex={sidebarOpen ? undefined : -1}
      >
        <nav aria-label="Điều hướng chính">
          <div className="sidebar-home-item">
            <Button
              className={`nav-item ${page === "Assistant" ? "active" : ""}`}
              aria-label="Trang chủ"
              aria-current={page === "Assistant" ? "page" : undefined}
              onClick={() => go("Assistant")}
            >
              <House size={18} />
              <span>Trang chủ</span>
              {page === "Assistant" && <i />}
            </Button>
            <Button
              className="sidebar-collapse-btn"
              aria-label="Thu gọn thanh menu"
              title="Thu gọn menu (Ctrl+B)"
              onClick={() => setSidebarOpen(false)}
            >
              <PanelLeftClose aria-hidden="true" size={15} />
            </Button>
          </div>
          {destinations.slice(1).map((n) => (
            <Button
              key={n.name}
              className={`nav-item ${page === n.name ? "active" : ""}`}
              aria-label={n.label}
              aria-current={page === n.name ? "page" : undefined}
              onClick={() => go(n.name)}
            >
              <n.icon size={18} />
              <span>{n.label}</span>
              {n.name === "Planner" && proposal && (
                <span className="nav-badge">Chờ duyệt</span>
              )}
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
          <Assistant
            onOpenPlanner={() => go("Planner")}
            onServerChange={() => void server.reload()}
          />
          <aside className="home-summary" aria-label="Tổng quan việc học">
            <HomeSummary tasks={tasks} go={go} />
          </aside>
        </div>
        {page === "Planner" && (
          <Planner
            tasks={tasks}
            events={apiEnabled ? server.events : tasks}
            userId={session?.user.id ?? "demo"}
            conversationId={conversationId}
            reload={server.reload}
            setTasks={setTasks}
            availability={availability}
            setAvailability={setAvailability}
            proposal={proposal}
            setProposal={setProposal}
            revision={revision}
            setRevision={setRevision}
            notify={setNotice}
          />
        )}
        <div
          hidden={page !== "Study"}
          className={page === "Study" ? "study-page-wrapper" : ""}
        >
          <Study />
        </div>
      </main>
      {modal === "account" && apiEnabled && (
        <Modal title="Tài khoản" close={() => setModal("")}>
          <p>Đăng nhập với {email}.</p>
          <Button
            className="secondary"
            onClick={() => {
              setModal("")

              void signOut()
            }}
          >
            Đăng xuất
          </Button>
        </Modal>
      )}
      {infoModal && !(modal === "account" && apiEnabled) && (
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
