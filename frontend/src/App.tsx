import { useEffect, useRef, useState } from "react"
import {
  ArrowUpRight,
  Bell,
  BookOpen,
  CalendarDays,
  ChevronDown,
  Check,
  CircleHelp,
  House,
  LayoutDashboard,
  Search,
  Settings,
  X,
} from "lucide-react"
import Button from "./components/ui/Button"
import Modal from "./components/ui/Modal"
import Assistant from "./features/assistant/Assistant"
import Dashboard from "./pages/Dashboard"
import Planner from "./pages/Planner"
import Study from "./pages/Study"
import type { Task } from "./types/task"

const destinations = [
  { name: "Assistant", label: "Trang chủ", icon: House },
  { name: "Dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { name: "Planner", label: "Lập kế hoạch", icon: CalendarDays },
  { name: "Study", label: "Học tập", icon: BookOpen },
]

const pageInfo: Record<string, { title: string; description: string }> = {
  Dashboard: {
    title: "Tổng quan",
    description: "Tổng quan việc học và hạn chót.",
  },
  Planner: {
    title: "Lập kế hoạch",
    description: "Quản lý công việc và lịch trong tuần.",
  },
  Study: {
    title: "Học tập",
    description: "Tài liệu và ghi chú cho buổi học.",
  },
}

const infoModals: Record<string, { title: string; text: string }> = {
  notifications: { title: "Thông báo của bạn", text: "Chưa có thông báo nào." },
  account: { title: "Tài khoản", text: "Chưa kết nối tài khoản." },
  settings: { title: "Cài đặt", text: "Chưa có cài đặt nào." },
  help: { title: "Trợ giúp & phản hồi", text: "Chưa có nội dung trợ giúp." },
}

export default function App() {
  const [page, setPage] = useState("Assistant")
  const [tasks, setTasks] = useState<Task[]>([])
  const [query, setQuery] = useState("")
  const [modal, setModal] = useState("")
  const [notice, setNotice] = useState("")
  const searchRef = useRef<HTMLInputElement>(null)
  const mainHeadingRef = useRef<HTMLHeadingElement>(null)
  const firstPage = useRef(true)
  const searchRequested = useRef(false)

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
    if (searchRequested.current && page === "Planner") {
      searchRef.current?.focus()
      searchRequested.current = false
    }
    window.scrollTo({ top: 0, behavior: "instant" })
  }, [page])
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        if (page === "Assistant") {
          searchRequested.current = true
          setPage("Planner")
        } else searchRef.current?.focus()
      }
    }
    document.addEventListener("keydown", fn)
    return () => document.removeEventListener("keydown", fn)
  }, [page])

  const go = (p: string) => {
    setPage(p)
    setQuery("")
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
            width={1600}
            height={400}
            fetchPriority="high"
          />
        </div>
        {page !== "Assistant" && (
          <div className="search-wrap">
            <Search aria-hidden="true" size={17} />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                if (page !== "Planner") setPage("Planner")
              }}
              placeholder="Tìm kiếm công việc..."
              aria-label="Tìm kiếm công việc"
            />
            <kbd>⌘ K</kbd>
          </div>
        )}
        <div className="top-actions">
          <Button
            className="icon-button notification"
            aria-label="Thông báo"
            onClick={() => setModal("notifications")}
          >
            <Bell aria-hidden="true" size={19} />
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
            <ChevronDown aria-hidden="true" size={14} />
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
              <n.icon size={19} />
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
          <Button
            className="nav-item"
            aria-label="Trợ giúp và phản hồi"
            onClick={() => setModal("help")}
          >
            <CircleHelp aria-hidden="true" size={18} />
            <span>Trợ giúp & phản hồi</span>
            <ArrowUpRight aria-hidden="true" size={13} />
          </Button>
        </div>
      </aside>
      <main
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
              <p>{info.description}</p>
            </div>
          </div>
        )}
        <div hidden={page !== "Assistant"}>
          <Assistant onOpenPlanner={() => go("Planner")} />
        </div>
        {page === "Dashboard" && (
          <Dashboard tasks={tasks} setTasks={setTasks} go={go} />
        )}
        {page === "Planner" && (
          <Planner
            tasks={tasks}
            setTasks={setTasks}
            query={query}
            notify={setNotice}
          />
        )}
        <div hidden={page !== "Study"}>
          <Study notify={setNotice} />
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
