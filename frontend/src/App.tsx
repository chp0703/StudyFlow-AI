import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type ButtonHTMLAttributes,
  useId,
} from "react"
import {
  BookOpen,
  LayoutDashboard,
  CalendarDays,
  Timer,
  ChartNoAxesCombined,
  FolderOpen,
  Sparkles,
  FileText,
  Settings,
  CircleHelp,
  Search,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ArrowUpRight,
  Check,
  Clock3,
  X,
  ArrowRight,
  Play,
  CheckCheck,
  AlertTriangle,
  Upload,
  Pause,
  Circle,
  ArrowLeft,
  ShieldCheck,
  House,
} from "lucide-react"
import Assistant from "./Assistant"
const demoToday = new Date()
demoToday.setHours(12, 0, 0, 0)
const demoDate = (offset: number) => {
  const date = new Date(demoToday)
  date.setDate(date.getDate() + offset)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`
}
const displayDemoDate = (offset: number) =>
  new Date(
    demoToday.getFullYear(),
    demoToday.getMonth(),
    demoToday.getDate() + offset,
  ).toLocaleDateString("vi-VN", { day: "numeric", month: "long" })
type Task = {
  id: number
  title: string
  course: string
  time: string
  done: boolean
  effort: number
  priority: string
  deadline: string
}
const initialTasks: Task[] = [
  {
    id: 1,
    title: "Ôn tập ghi chú bài giảng",
    course: "Giải tích",
    time: "09:00 – 10:00",
    done: true,
    effort: 60,
    priority: "Trung bình",
    deadline: demoDate(4),
  },
  {
    id: 2,
    title: "Luyện đạo hàm riêng",
    course: "Giải tích",
    time: "10:30 – 11:30",
    done: false,
    effort: 60,
    priority: "Cao",
    deadline: demoDate(7),
  },
  {
    id: 3,
    title: "Họp dự án nhóm",
    course: "Kỹ thuật phần mềm",
    time: "14:00 – 15:00",
    done: false,
    effort: 60,
    priority: "Trung bình",
    deadline: demoDate(4),
  },
  {
    id: 4,
    title: "Chuẩn bị bài thực hành mạng",
    course: "Mạng máy tính",
    time: "16:00 – 17:00",
    done: false,
    effort: 60,
    priority: "Trung bình",
    deadline: demoDate(11),
  },
]
const deadlines = [
  {
    title: "Báo cáo dự án",
    course: "Kỹ thuật phần mềm",
    date: displayDemoDate(4),
    days: "Còn 4 ngày · dữ liệu mẫu",
    urgent: true,
  },
  {
    title: "Bài tập 3",
    course: "Giải tích",
    date: displayDemoDate(7),
    days: "Còn 7 ngày · dữ liệu mẫu",
    urgent: false,
  },
  {
    title: "Thi giữa kỳ",
    course: "Mạng máy tính",
    date: displayDemoDate(11),
    days: "Còn 11 ngày · dữ liệu mẫu",
    urgent: false,
  },
]
const destinations = [
  { name: "Assistant", label: "Trang chủ", icon: House },
  { name: "Dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { name: "Planner", label: "Lập kế hoạch", icon: CalendarDays },
  { name: "Study", label: "Học tập", icon: BookOpen },
]
function Button({
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
function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section
      id={className === "focus-hero" ? "focus-card" : undefined}
      className={`card ${className}`}
    >
      {title && (
        <div className="card-heading">
          <h2>{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}
function Modal({
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

export default function App() {
  const [page, setPage] = useState("Assistant"),
    [tasks, setTasks] = useState(initialTasks),
    [query, setQuery] = useState(""),
    [modal, setModal] = useState(""),
    [notice, setNotice] = useState(""),
    [week, setWeek] = useState(0),
    [selectedDay, setSelectedDay] = useState((demoToday.getDay() + 6) % 7),
    [period, setPeriod] = useState("Week")
  const [edit, setEdit] = useState<Task | null>(null),
    [name, setName] = useState(""),
    [course, setCourse] = useState("Giải tích"),
    [effort, setEffort] = useState(30),
    [remaining, setRemaining] = useState(30),
    [priority, setPriority] = useState("Trung bình"),
    [deadline, setDeadline] = useState(demoDate(4)),
    [capacity, setCapacity] = useState(60),
    [proposalDuration, setProposalDuration] = useState(30)
  const [running, setRunning] = useState(false),
    [seconds, setSeconds] = useState(1080),
    [reflection, setReflection] = useState(""),
    [sessionSaved, setSessionSaved] = useState(false),
    [answer, setAnswer] = useState(""),
    [quizState, setQuizState] = useState("setup"),
    [reviewTab, setReviewTab] = useState("Practice"),
    [revision, setRevision] = useState(false),
    [filter, setFilter] = useState("Tất cả môn học")
  const [files, setFiles] = useState<{
    name: string
    course: string
    status: string
  }[]>([])
  const [studyMode, setStudyMode] =
    useState<"overview" | "exercise" | "answer">("overview")
  const [studyQuestion, setStudyQuestion] = useState("")
  const [studyAnswer, setStudyAnswer] = useState("")
  const [studyResponse, setStudyResponse] = useState("")
  const [plannerPrompt, setPlannerPrompt] = useState("")
  const [plannerSource, setPlannerSource] = useState("")
  const [selectedDeadline, setSelectedDeadline] = useState(deadlines[0])
  const uploadRef = useRef<HTMLInputElement>(null)
  const plannerUploadRef = useRef<HTMLInputElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const mainHeadingRef = useRef<HTMLHeadingElement>(null)
  const firstPage = useRef(true)
  const searchRequested = useRef(false)
  useEffect(() => {
    document.documentElement.lang = "vi"
  }, [])
  useEffect(() => {
    document.title = `${
      {
        Dashboard: "Tổng quan",
        Planner: "Lập kế hoạch",
        Study: "Học tập",
        Assistant: "Trang chủ",
        Review: "Ôn tập",
        Materials: "Tài liệu",
      }[page] || page
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
    if (!running) return
    const id = setInterval(() => setSeconds((v) => v + 1), 1000)
    return () => clearInterval(id)
  }, [running])
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
  const notify = (s: string) => {
    setNotice(s)
  }
  const monday = new Date(demoToday)
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7) + week * 7)
  const date = monday
  const weekDays = Array.from(
    { length: 7 },
    (_, i) =>
      new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i),
  )
  const plan = () => {
    setProposalDuration(30)
    setModal("proposal")
  }
  const completedTasks = tasks.filter((task) => task.done).length
  const filteredTasks = tasks.filter((task) =>
    `${task.title} ${task.course}`
      .toLocaleLowerCase("vi")
      .includes(query.trim().toLocaleLowerCase("vi")),
  )
  return (
    <div className="app-shell">
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
        {page !== "Assistant" && (
          <div className="page-heading">
            <div>
              <h1 ref={mainHeadingRef} tabIndex={-1}>
                {{
                  Dashboard: "Tổng quan",
                  Planner: "Lập kế hoạch",
                  Study: "Học tập",
                  Review: "Ôn tập",
                  Materials: "Tài liệu",
                }[page] || page}
              </h1>
              <p>
                {page === "Dashboard"
                  ? "Tổng quan việc học và lịch trong tuần."
                  : page === "Planner"
                    ? "Quản lý công việc, thời gian rảnh và lịch minh họa trong phiên."
                    : page === "Study"
                      ? "Đọc tài liệu và ghi chú cho buổi học."
                      : page === "Review"
                        ? "Luyện câu hỏi và xem lại câu trả lời."
                        : "Ghi chú và tài liệu môn học của bạn ở một nơi."}
              </p>
            </div>
            {page === "Planner" ? (
              <Button className="primary" onClick={plan}>
                <Sparkles aria-hidden="true" size={16} />
                Tạo kế hoạch học
              </Button>
            ) : page === "Study" ? (
              <Button
                className="primary"
                onClick={() => uploadRef.current?.click()}
              >
                <Upload aria-hidden="true" size={16} />
                Thêm tài liệu
              </Button>
            ) : null}
          </div>
        )}
        <div hidden={page !== "Assistant"}>
          <Assistant onOpenPlanner={() => go("Planner")} />
        </div>
        {page === "Dashboard" && (
          <>
            <div
              className="dashboard-summary"
              role="group"
              aria-label="Tổng quan việc học"
            >
              <Card className="summary-card summary-purple">
                <div className="summary-main">
                  <span className="summary-icon">
                    <CheckCheck aria-hidden="true" size={27} />
                  </span>
                  <div>
                    <strong>
                      {completedTasks} <span>/ {tasks.length}</span>
                    </strong>
                    <p>Công việc đã hoàn thành</p>
                  </div>
                </div>
                <div
                  className="summary-progress"
                  role="progressbar"
                  aria-label="Công việc minh họa đã hoàn thành"
                  aria-valuenow={completedTasks}
                  aria-valuemin={0}
                  aria-valuemax={Math.max(tasks.length, 1)}
                >
                  <i
                    style={{
                      width: `${
                        tasks.length ? (completedTasks / tasks.length) * 100 : 0
                      }%`,
                    }}
                  />
                </div>
              </Card>
              <Card className="summary-card summary-rose">
                <Button
                  className="summary-link"
                  onClick={() => {
                    go("Planner")
                  }}
                  aria-label="Xem các hạn chót sắp tới"
                >
                  <div className="summary-main">
                    <span className="summary-icon">
                      <CalendarDays aria-hidden="true" size={27} />
                    </span>
                    <div>
                      <strong>{deadlines.length}</strong>
                      <p>Hạn chót sắp tới</p>
                    </div>
                  </div>
                  <ChevronRight aria-hidden="true" size={20} />
                </Button>
              </Card>
              <Card className="summary-card summary-green">
                <div className="summary-main">
                  <span className="summary-icon">
                    <ChartNoAxesCombined aria-hidden="true" size={29} />
                  </span>
                  <div>
                    <strong>
                      5 <span>ngày</span>
                    </strong>
                    <p>Chuỗi ngày học</p>
                  </div>
                </div>
              </Card>
              <Card className="summary-card summary-blue">
                <div className="summary-main">
                  <span className="summary-icon">
                    <Clock3 aria-hidden="true" size={28} />
                  </span>
                  <div>
                    <strong>
                      12,5 <span>giờ</span>
                    </strong>
                    <p>Tổng thời gian học (tuần này)</p>
                  </div>
                </div>
              </Card>
            </div>
            <p className="workspace-demo-note">
              Dữ liệu công việc và tiến độ trên trang này là ví dụ minh họa
              trong phiên hiện tại.
            </p>
            <div className="dashboard-today-grid">
              <Card
                title="Công việc trong phiên"
                action={
                  <span className="count-label">{tasks.length} CÔNG VIỆC</span>
                }
              >
                <div className="today-task-list">
                  {tasks.length === 0 && (
                    <div className="empty-inline">
                      <p>Chưa có công việc trong phiên mẫu.</p>
                      <Button
                        className="text-button"
                        onClick={() => go("Planner")}
                      >
                        Mở Lập kế hoạch
                      </Button>
                    </div>
                  )}
                  {tasks.map((task) => (
                    <div
                      className={`today-task-row ${
                        task.done ? "complete" : ""
                      }`}
                      key={task.id}
                    >
                      <input
                        type="checkbox"
                        className="task-checkbox"
                        checked={task.done}
                        aria-label={`Đánh dấu ${task.title} ${
                          task.done ? "chưa hoàn thành" : "hoàn thành"
                        }`}
                        onChange={() =>
                          setTasks(
                            tasks.map((item) =>
                              item.id === task.id
                                ? { ...item, done: !item.done }
                                : item,
                            ),
                          )
                        }
                      />
                      <div className="task-info">
                        <strong>{task.title}</strong>
                        <span>{task.course}</span>
                      </div>
                      <span className="task-time">{task.time}</span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card
                title="Deadline sắp tới"
                action={
                  <span className="count-label">
                    {deadlines.length} HẠN CHÓT
                  </span>
                }
              >
                <div className="deadline-list">
                  {deadlines.map((deadline) => (
                    <Button
                      className="deadline-row"
                      key={deadline.title}
                      onClick={() => {
                        setSelectedDeadline(deadline)
                        setModal("deadline")
                      }}
                    >
                      <span
                        className={`deadline-dot ${
                          deadline.urgent ? "urgent" : ""
                        }`}
                      />
                      <span className="deadline-info">
                        <strong>{deadline.title}</strong>
                        <small>{deadline.course}</small>
                      </span>
                      <span className="deadline-date">
                        <strong>{deadline.date}</strong>
                        <small>{deadline.days}</small>
                      </span>
                    </Button>
                  ))}
                </div>
              </Card>
            </div>
          </>
        )}
        {page === "Planner" && (
          <>
            <div className="page-toolbar">
              <div>
                <Button
                  className="secondary"
                  onClick={() => setModal("availability")}
                >
                  <Clock3 aria-hidden="true" size={15} />
                  Thời gian rảnh
                </Button>
              </div>
              <div>
                <Button
                  className="primary"
                  onClick={() => {
                    setEdit(null)
                    setName("")
                    setCourse("Giải tích")
                    setEffort(30)
                    setRemaining(30)
                    setPriority("Trung bình")
                    setDeadline(demoDate(4))
                    setModal("task")
                  }}
                >
                  Thêm công việc
                </Button>
              </div>
            </div>
            <Card
              className="planner-task-card"
              title="Công việc mẫu"
              action={
                <span className="count-label">
                  {filteredTasks.length} CÔNG VIỆC
                </span>
              }
            >
              {filteredTasks.length ? (
                <div className="planner-task-list">
                  {filteredTasks.map((task) => (
                    <div className="planner-task-row" key={task.id}>
                      <input
                        type="checkbox"
                        className="task-checkbox"
                        checked={task.done}
                        aria-label={`Đánh dấu ${task.title} ${
                          task.done ? "chưa hoàn thành" : "hoàn thành"
                        }`}
                        onChange={() =>
                          setTasks((items) =>
                            items.map((item) =>
                              item.id === task.id
                                ? { ...item, done: !item.done }
                                : item,
                            ),
                          )
                        }
                      />
                      <div className="planner-task-info">
                        <strong className={task.done ? "is-done" : ""}>
                          {task.title}
                        </strong>
                        <span>
                          {task.course} · {task.time}
                        </span>
                      </div>
                      <span
                        className={`priority-badge ${
                          task.priority === "Cao" ? "is-high" : ""
                        }`}
                      >
                        {task.priority}
                      </span>
                      <time dateTime={task.deadline}>
                        Hạn{" "}
                        {new Date(
                          `${task.deadline}T12:00:00`,
                        ).toLocaleDateString("vi-VN", {
                          day: "numeric",
                          month: "numeric",
                          year: "numeric",
                        })}
                      </time>
                      <Button
                        className="secondary"
                        onClick={() => {
                          setEdit(task)
                          setName(task.title)
                          setCourse(task.course)
                          setEffort(task.effort)
                          setRemaining(task.effort)
                          setPriority(task.priority)
                          setDeadline(task.deadline)
                          setModal("task")
                        }}
                      >
                        Chỉnh sửa
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-inline">
                  <p>
                    {query.trim()
                      ? "Không có công việc phù hợp với từ khóa."
                      : "Chưa có công việc trong bản mẫu."}
                  </p>
                  <Button
                    className="primary"
                    onClick={() => {
                      setEdit(null)
                      setName("")
                      setDeadline(demoDate(4))
                      setModal("task")
                    }}
                  >
                    Thêm công việc
                  </Button>
                </div>
              )}
            </Card>
            <input
              className="hidden"
              ref={plannerUploadRef}
              type="file"
              accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
              onChange={(e) => {
                setPlannerSource(e.target.files?.[0]?.name || "")
                e.target.value = ""
              }}
            />
            <Card className="planner-ai-panel" title="Phác thảo lịch học">
              <div className="planner-ai-content">
                <p>
                  Chọn tên tệp và mô tả mong muốn của bạn. Bản mẫu hiện chưa đọc
                  nội dung tệp hoặc phân tích yêu cầu bằng AI; đề xuất bên dưới
                  là ví dụ cố định để bạn xem và xác nhận trong phiên.
                </p>
                <div className="planner-ai-actions">
                  <Button
                    className="secondary"
                    onClick={() => plannerUploadRef.current?.click()}
                  >
                    <Upload aria-hidden="true" size={16} />
                    {plannerSource ? "Đổi tệp mẫu" : "Chọn tên tệp mẫu"}
                  </Button>
                  {plannerSource && <span>{plannerSource}</span>}
                </div>
                <textarea
                  aria-label="Yêu cầu điều chỉnh lịch"
                  value={plannerPrompt}
                  onChange={(e) => setPlannerPrompt(e.target.value)}
                  placeholder="Ví dụ: Ưu tiên Giải tích trước thứ Sáu và không xếp lịch sau 18:00..."
                />
                <Button className="primary" onClick={plan}>
                  <Sparkles aria-hidden="true" size={16} />
                  Xem đề xuất minh họa
                </Button>
              </div>
            </Card>
            {revision && (
              <div className="info-banner">
                <Sparkles aria-hidden="true" size={18} />
                <div>
                  <strong>Đề xuất ôn tập từ mục Ôn tập</strong>
                  <p>
                    Ôn lại đạo hàm riêng dựa trên bài kiểm tra minh họa. Nội
                    dung này chưa được lên lịch.
                  </p>
                </div>
                <Button className="text-button" onClick={plan}>
                  Xem đề xuất <ArrowRight aria-hidden="true" size={14} />
                </Button>
              </div>
            )}
            {capacity < 30 && (
              <div className="warning-banner">
                <AlertTriangle aria-hidden="true" size={20} />
                <div>
                  <strong>Không đủ thời gian trống</strong>
                  <p>
                    Không thể sắp xếp buổi học 30 phút trong {capacity} phút
                    thời gian rảnh. Chưa có thay đổi nào được thực hiện.
                  </p>
                </div>
                <Button
                  className="text-button"
                  onClick={() => setModal("availability")}
                >
                  Chỉnh sửa thời gian rảnh
                </Button>
              </div>
            )}
            <Card
              className="dashboard-calendar"
              title="Lịch"
              action={
                <div className="dashboard-calendar-controls">
                  <span>
                    {date.toLocaleDateString("vi-VN", {
                      month: "long",
                      year: "numeric",
                    })}
                  </span>
                  <Button
                    className="secondary"
                    onClick={() => {
                      setWeek(0)
                      setSelectedDay((demoToday.getDay() + 6) % 7)
                    }}
                  >
                    Hôm nay
                  </Button>
                  <Button
                    className="icon-button"
                    aria-label="Tuần trước"
                    onClick={() => setWeek(week - 1)}
                  >
                    <ChevronLeft aria-hidden="true" size={18} />
                  </Button>
                  <Button
                    className="icon-button"
                    aria-label="Tuần sau"
                    onClick={() => setWeek(week + 1)}
                  >
                    <ChevronRight aria-hidden="true" size={18} />
                  </Button>
                  <select
                    aria-label="Chế độ xem lịch"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                  >
                    <option value="Week">Tuần</option>
                    <option value="Hôm nay">Ngày</option>
                  </select>
                </div>
              }
            >
              <div
                className="dashboard-calendar-scroll"
                role="region"
                aria-label="Lịch trong tuần, cuộn ngang để xem tất cả các ngày"
                tabIndex={0}
              >
                <div
                  className={`dashboard-schedule ${
                    period === "Hôm nay" ? "day-view" : ""
                  }`}
                >
                  <div className="schedule-header">
                    <span className="schedule-timezone">Giờ địa phương</span>
                    {weekDays.map((d, i) =>
                      period === "Hôm nay" && i !== selectedDay ? null : (
                        <Button
                          key={i}
                          className={`schedule-day ${
                            week === 0 && i === (demoToday.getDay() + 6) % 7
                              ? "is-today"
                              : ""
                          }`}
                          onClick={() => {
                            setSelectedDay(i)
                            setPeriod("Hôm nay")
                          }}
                        >
                          <span>
                            {["T2", "T3", "T4", "T5", "T6", "T7", "CN"][i]}
                          </span>
                          <strong>{d.getDate()}</strong>
                        </Button>
                      ),
                    )}
                  </div>
                  {Array.from({ length: 10 }, (_, i) => i + 8).map((hour) => (
                    <div className="schedule-row" key={hour}>
                      <span className="schedule-hour">
                        {String(hour).padStart(2, "0")}:00
                      </span>
                      {weekDays.map((_, day) => {
                        if (period === "Hôm nay" && day !== selectedDay)
                          return null
                        const events =
                          week === 0
                            ? [
                                {
                                  day: 0,
                                  hour: 9,
                                  title: "Ôn tập ghi chú bài giảng",
                                  course: "Giải tích",
                                  time: "09:00–10:00",
                                  kind: "study",
                                },
                                {
                                  day: 0,
                                  hour: 11,
                                  title: "Bài tập luyện",
                                  course: "Giải tích",
                                  time: "11:00–12:00",
                                  kind: "study",
                                },
                                {
                                  day: 0,
                                  hour: 14,
                                  title: "Họp dự án nhóm",
                                  course: "Kỹ thuật phần mềm",
                                  time: "14:00–15:00",
                                  kind: "meeting",
                                },
                                {
                                  day: 0,
                                  hour: 16,
                                  title: "Chuẩn bị bài thực hành",
                                  course: "Mạng máy tính",
                                  time: "16:00–17:00",
                                  kind: "study",
                                },
                                {
                                  day: 1,
                                  hour: 10,
                                  title: "Làm bài tập",
                                  course: "Giải tích",
                                  time: "10:00–11:00",
                                  kind: "study",
                                },
                                {
                                  day: 2,
                                  hour: 9,
                                  title: "Chuẩn bị bài thực hành",
                                  course: "Mạng máy tính",
                                  time: "09:00–10:00",
                                  kind: "study",
                                },
                                {
                                  day: 3,
                                  hour: 14,
                                  title: "Họp nhóm",
                                  course: "Kỹ thuật phần mềm",
                                  time: "14:00–15:00",
                                  kind: "meeting",
                                },
                                {
                                  day: 4,
                                  hour: 10,
                                  title: "Báo cáo dự án due",
                                  course: "Kỹ thuật phần mềm",
                                  time: "Hạn lúc 11:00",
                                  kind: "deadline",
                                },
                                {
                                  day: 5,
                                  hour: 11,
                                  title: "Chuẩn bị cho kỳ thi",
                                  course: "Giải tích",
                                  time: "11:00–12:00",
                                  kind: "study",
                                },
                              ]
                            : []
                        const event = events.find(
                          (e) => e.day === day && e.hour === hour,
                        )
                        return (
                          <div
                            className={`schedule-cell ${
                              week === 0 && day === (demoToday.getDay() + 6) % 7
                                ? "today-column"
                                : ""
                            }`}
                            key={day}
                          >
                            {event && (
                              <Button
                                aria-label={`${weekDays[day].toLocaleDateString("vi-VN", { weekday: "long", month: "long", day: "numeric" })}, ${event.title}, ${event.kind}, ${event.time}`}
                                className={`schedule-event ${event.kind}`}
                                onClick={() =>
                                  event.kind === "deadline"
                                    ? setModal("deadline")
                                    : go("Study")
                                }
                              >
                                <strong>{event.title}</strong>
                                <span>{event.course}</span>
                                <small>{event.time}</small>
                              </Button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>
              </div>
              <div className="schedule-legend">
                <span>
                  <i className="legend-study" />
                  Buổi học
                </span>
                <span>
                  <i className="legend-meeting" />
                  Cuộc họp
                </span>
                <span>
                  <i className="legend-deadline" />
                  Hạn chót
                </span>
              </div>
            </Card>
          </>
        )}
        {page === "Study" && (
          <>
            <input
              className="hidden"
              ref={uploadRef}
              type="file"
              accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
              multiple
              onChange={(e) => {
                setFiles([
                  ...files,
                  ...Array.from(e.target.files || []).map((file) => ({
                    name: file.name,
                    course: "Chưa phân loại",
                    status: "Chỉ lưu tên tệp trong phiên · chưa đọc nội dung",
                  })),
                ])
                e.target.value = ""
              }}
            />
            <Card className="study-tools" title="Học cùng tài liệu">
              <div className="study-tools-content">
                <div className="study-material-summary">
                  <FileText aria-hidden="true" size={20} />
                  <div>
                    <strong>
                      {files.length
                        ? `${files.length} tên tệp đã chọn`
                        : "Chưa chọn tệp"}
                    </strong>
                    <p>
                      Bản mẫu chỉ ghi tên tệp. Bài tập và câu trả lời bên dưới
                      không dựa trên nội dung của tệp đã chọn.
                    </p>
                  </div>
                  <Button
                    className="secondary"
                    onClick={() => uploadRef.current?.click()}
                  >
                    <Upload aria-hidden="true" size={16} />
                    Chọn tệp
                  </Button>
                </div>
                <div className="study-feature-grid">
                  <Button
                    className="study-feature"
                    onClick={() => {
                      setStudyMode("exercise")
                      setStudyQuestion(
                        "Nếu f(x, y) = x²y, đạo hàm riêng theo x là gì?",
                      )
                      setStudyAnswer("")
                      setStudyResponse("")
                    }}
                  >
                    <Sparkles aria-hidden="true" size={18} />
                    <span>
                      <strong>Bài tập minh họa</strong>
                      <small>Câu hỏi có sẵn, chưa đọc tài liệu</small>
                    </span>
                    <ArrowRight aria-hidden="true" size={15} />
                  </Button>
                  <form
                    className="study-question"
                    onSubmit={(e) => {
                      e.preventDefault()
                      if (!studyQuestion.trim()) return
                      setStudyMode("answer")
                      setStudyResponse(
                        /đạo hàm|f\(x/iu.test(studyQuestion)
                          ? "Với ví dụ f(x, y) = x²y, hãy giữ y không đổi và lấy đạo hàm x². Kết quả là 2xy. Đây là câu trả lời mẫu, không dựa trên tệp đã chọn."
                          : "Bản mẫu chỉ hỗ trợ ví dụ đạo hàm riêng có sẵn. Câu hỏi của bạn chưa được gửi tới AI hoặc đối chiếu với tài liệu.",
                      )
                    }}
                  >
                    <label htmlFor="study-question-input">
                      Hỏi trong bản mẫu
                    </label>
                    <div>
                      <input
                        id="study-question-input"
                        value={studyQuestion}
                        onChange={(e) => setStudyQuestion(e.target.value)}
                        placeholder="Bạn còn thắc mắc điều gì?"
                      />
                      <Button
                        className="primary"
                        type="submit"
                        aria-label="Gửi câu hỏi"
                      >
                        <ArrowRight aria-hidden="true" size={16} />
                      </Button>
                    </div>
                  </form>
                </div>
                {studyMode === "exercise" && (
                  <div className="study-exercise">
                    <span className="eyebrow">BÀI TẬP MINH HỌA</span>
                    <h3>{studyQuestion}</h3>
                    <div className="exercise-options">
                      {["2xy", "x²", "2x + y"].map((option) => (
                        <label key={option}>
                          <input
                            type="radio"
                            name="study-answer"
                            value={option}
                            checked={studyAnswer === option}
                            onChange={() => setStudyAnswer(option)}
                          />
                          {option}
                        </label>
                      ))}
                    </div>
                    <Button
                      className="primary"
                      disabled={!studyAnswer}
                      onClick={() => {
                        setStudyMode("answer")
                        setStudyResponse(
                          studyAnswer === "2xy"
                            ? "Chính xác. Giữ y không đổi, đạo hàm theo x là 2xy."
                            : "Hãy xem lại cách giữ y không đổi. Đáp án đúng là 2xy.",
                        )
                      }}
                    >
                      Kiểm tra đáp án
                    </Button>
                  </div>
                )}
                {studyMode === "answer" && studyResponse && (
                  <div className="info-banner study-response">
                    <BookOpen aria-hidden="true" size={18} />
                    <p>{studyResponse}</p>
                  </div>
                )}
              </div>
            </Card>
            <div className="study-session-bar">
              <span className="course-icon">
                <BookOpen aria-hidden="true" size={21} />
              </span>
              <div>
                <strong>Đạo hàm riêng</strong>
                <p>Giải tích · Chương 3 · Dự kiến 60 phút</p>
              </div>
              <span
                className="timer"
                role="timer"
                aria-label="Thời gian đã trôi qua của buổi học"
              >
                {String(Math.floor(seconds / 60)).padStart(2, "0")}:
                {String(seconds % 60).padStart(2, "0")}
              </span>
              <Button
                className="secondary"
                onClick={() => setRunning(!running)}
              >
                {running ? (
                  <Pause aria-hidden="true" size={15} />
                ) : (
                  <Play aria-hidden="true" size={15} />
                )}{" "}
                {running ? "Pause" : "Tiếp tục"}
              </Button>
              <Button
                className="primary"
                onClick={() => {
                  setRunning(false)
                  setModal("reflection")
                }}
              >
                Kết thúc buổi học <ArrowRight aria-hidden="true" size={15} />
              </Button>
            </div>
            {sessionSaved && (
              <div className="info-banner">
                <Check aria-hidden="true" size={18} />
                <div>
                  <strong>Đã xác nhận kết quả buổi học</strong>
                  <p>
                    Phản hồi của bạn is recorded for this prototype session.
                    Thời gian học không chứng minh mức độ thành thạo.
                  </p>
                </div>
                <Button className="text-button" onClick={() => go("Study")}>
                  Làm bài luyện tập <ArrowRight aria-hidden="true" size={14} />
                </Button>
              </div>
            )}
            <div className="study-grid">
              <Card
                title="Tài liệu học tập"
                action={
                  <span className="quiet-badge">GHI CHÚ MINH HỌA · §3.1</span>
                }
              >
                <article className="document">
                  <span className="eyebrow">GIẢI TÍCH / CHƯƠNG 3</span>
                  <h2>Tìm hiểu về đạo hàm riêng</h2>
                  <p>
                    When a function depends on more than one variable, a partial
                    derivative measures how it changes with respect to one
                    variable while keeping the others fixed.
                  </p>
                  <h3>Ví dụ minh họa</h3>
                  <div
                    className="formula"
                    role="math"
                    aria-label="f of x y equals x squared times y plus three y"
                  >
                    f(x, y) = x²y + 3y
                  </div>
                  <p>
                    To differentiate with respect to x, hold y constant. The
                    derivative of x²y is 2xy, and the derivative of 3y with
                    respect to x is zero.
                  </p>
                  <div
                    className="formula result"
                    role="math"
                    aria-label="Đạo hàm riêng của f theo x bằng hai x y"
                  >
                    ∂f / ∂x = 2xy
                  </div>
                  <div className="document-callout">
                    <BookOpen aria-hidden="true" size={18} />
                    <p>
                      Đây là ví dụ do tác giả biên soạn, không phải tài liệu môn
                      học được trích xuất hoặc xác minh.
                    </p>
                  </div>
                  <h3>Tự thử sức</h3>
                  <p>
                    Điều gì thay đổi nếu bạn lấy đạo hàm cùng hàm số theo biến
                    y?
                  </p>
                </article>
              </Card>
              <div>
                <Card title="Ghi chú buổi học">
                  <textarea
                    className="session-notes"
                    aria-label="Ghi chú buổi học"
                    placeholder="Ghi lại câu hỏi, điều bạn hiểu được hoặc nội dung cần xem lại..."
                    value={reflection}
                    onChange={(e) => setReflection(e.target.value)}
                  />
                  <div className="planner-note">
                    Ghi chú chỉ được giữ trong thời gian mở bản thử nghiệm này.
                  </div>
                </Card>
              </div>
            </div>
          </>
        )}
        {page === "Review" && (
          <>
            <div
              className="tabs standalone"
              role="group"
              aria-label="Chế độ xem ôn tập"
            >
              {[
                { value: "Practice", label: "Luyện tập" },
                { value: "Progress", label: "Tiến độ" },
              ].map((tab) => (
                <Button
                  key={tab.value}
                  aria-pressed={reviewTab === tab.value}
                  className={reviewTab === tab.value ? "active" : ""}
                  onClick={() => setReviewTab(tab.value)}
                >
                  {tab.label}
                </Button>
              ))}
            </div>
            {reviewTab === "Progress" ? (
              <Card className="review-card">
                <div className="empty-state">
                  <ChartNoAxesCombined aria-hidden="true" size={38} />
                  <h2>Hiểu bài bắt đầu từ bằng chứng.</h2>
                  <p>
                    Chưa đủ dữ liệu. Chưa có bài đánh giá nào được xác minh
                    trong bản minh họa này. Một buổi học hoàn thành không phải
                    là thước đo mức độ thành thạo.
                  </p>
                  <Button
                    className="secondary"
                    onClick={() => setReviewTab("Practice")}
                  >
                    Xem phần luyện tập{" "}
                    <ArrowRight aria-hidden="true" size={15} />
                  </Button>
                </div>
              </Card>
            ) : (
              <Card
                className="review-card"
                title={
                  quizState === "results"
                    ? "Kết quả luyện tập"
                    : quizState === "question"
                      ? "Câu hỏi 1 trên 1"
                      : "Một bài kiểm tra nhanh mức độ hiểu bài"
                }
                action={<span className="quiet-badge">LUYỆN TẬP MINH HỌA</span>}
              >
                {quizState === "setup" ? (
                  <div className="review-setup">
                    <p>
                      Chọn một chủ đề và làm một câu hỏi mẫu. Bài đánh giá có
                      xác minh nguồn cần tài liệu học tập được cấp phép.
                    </p>
                    <div className="form-grid">
                      <label>
                        Môn học
                        <select
                          value={course}
                          onChange={(e) => setCourse(e.target.value)}
                        >
                          <option>Giải tích</option>
                          <option>Mạng máy tính</option>
                        </select>
                      </label>
                      <label>
                        Chủ đề
                        <select>
                          <option>
                            {course === "Giải tích"
                              ? "Đạo hàm riêng"
                              : "Giao thức mạng"}
                          </option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Nguồn học tập
                      <select>
                        <option>Không có nguồn đã xác minh</option>
                      </select>
                    </label>
                    <div className="warning-banner">
                      <AlertTriangle aria-hidden="true" size={18} />
                      <div>
                        <strong>Không đủ bằng chứng từ nguồn</strong>
                        <p>
                          Không thể tạo hoặc chấm bài kiểm tra có xác minh
                          nguồn. Bạn bạn có thể xem ví dụ Giải tích do tác giả
                          biên soạn; kết quả này không tạo ra điểm thành thạo đã
                          xác minh.
                        </p>
                      </div>
                    </div>
                    <Button
                      className="primary"
                      onClick={() => {
                        setCourse("Giải tích")
                        setAnswer("")
                        setQuizState("question")
                      }}
                    >
                      Bắt đầu bài kiểm tra mẫu{" "}
                      <ArrowRight aria-hidden="true" size={16} />
                    </Button>
                  </div>
                ) : quizState === "question" ? (
                  <div className="quiz-content">
                    <span className="eyebrow">GIẢI TÍCH · ĐẠO HÀM RIÊNG</span>
                    <h3>Nếu f(x, y) = x²y, ∂f/∂x bằng bao nhiêu?</h3>
                    <p>Giữ y không đổi khi lấy đạo hàm theo x.</p>
                    <fieldset className="quiz-choices">
                      <legend>Chọn một đáp án</legend>
                      {["2xy", "x²", "2x + y"].map((a, i) => (
                        <label
                          className={`quiz-answer ${
                            answer === a ? "chosen" : ""
                          }`}
                          key={a}
                        >
                          <input
                            type="radio"
                            name="quiz-answer"
                            value={a}
                            checked={answer === a}
                            onChange={() => setAnswer(a)}
                          />
                          <span>{["A", "B", "C"][i]}</span>
                          {a}
                        </label>
                      ))}
                    </fieldset>
                    <div className="source-disclaimer">
                      Nguồn: ghi chú minh họa do tác giả biên soạn, §3.1. Chưa
                      được xác minh bên ngoài.
                    </div>
                    <Button
                      className="primary"
                      disabled={!answer}
                      onClick={() => setModal("submit")}
                    >
                      Gửi đáp án <ArrowRight aria-hidden="true" size={15} />
                    </Button>
                  </div>
                ) : (
                  <div className="quiz-content">
                    <div className="result-heading">
                      <span className="result-icon">
                        {answer === "2xy" ? (
                          <Check aria-hidden="true" size={25} />
                        ) : (
                          <BookOpen aria-hidden="true" size={25} />
                        )}
                      </span>
                      <div>
                        <h3>
                          {answer === "2xy"
                            ? "Một bước tiến tốt."
                            : "Một nội dung hữu ích để xem lại."}
                        </h3>
                        <p>
                          {answer === "2xy" ? "1 trên 1" : "0 trên 1"} câu trả
                          lời mẫu đúng · Không phải bài đánh giá đã xác minh
                        </p>
                      </div>
                    </div>
                    <div className="answer-explanation">
                      <strong>Đáp án đúng: 2xy</strong>
                      <p>
                        Giữ y không đổi, đạo hàm của x² là 2x, nên ∂(x²y)/∂x =
                        2xy.
                      </p>
                      <span>
                        Ghi chú minh họa do tác giả biên soạn · §3.1 · Cỡ mẫu: 1
                        câu hỏi
                      </span>
                    </div>
                    {answer !== "2xy" && (
                      <div className="revision-card">
                        <Sparkles aria-hidden="true" size={19} />
                        <div>
                          <strong>Đề xuất ôn tập: Đạo hàm riêng</strong>
                          <p>
                            Dựa trên một câu trả lời mẫu chưa đúng, hãy ôn lại
                            cách giữ biến còn lại không đổi. Đây là gợi ý luyện
                            tập, không phải điểm yếu đã xác minh hay thay đổi
                            lịch học.
                          </p>
                          <Button
                            className="text-button"
                            onClick={() => {
                              setRevision(true)
                              go("Planner")
                              notify(
                                "Đã gửi gợi ý sang Lập kế hoạch. Lịch của bạn không thay đổi.",
                              )
                            }}
                          >
                            Gửi sang Lập kế hoạch{" "}
                            <ArrowRight aria-hidden="true" size={15} />
                          </Button>
                        </div>
                      </div>
                    )}
                    <Button
                      className="secondary"
                      onClick={() => setQuizState("setup")}
                    >
                      Quay lại luyện tập
                    </Button>
                  </div>
                )}
              </Card>
            )}
          </>
        )}
        {page === "Materials" && (
          <>
            <input
              className="hidden"
              ref={uploadRef}
              type="file"
              accept=".pdf,.txt"
              multiple
              onChange={(e) => {
                setFiles([
                  ...files,
                  ...Array.from(e.target.files || []).map((f) => ({
                    name: f.name,
                    course: "Unassigned",
                    status: "Chưa xử lý · chỉ xem trước trên máy",
                  })),
                ])
                e.target.value = ""
              }}
            />
            <div className="page-toolbar">
              <div className="tabs" role="group" aria-label="View options">
                {["Tất cả môn học", "Giải tích", "Mạng máy tính"].map((c) => (
                  <Button
                    key={c}
                    aria-pressed={filter === c}
                    className={filter === c ? "active" : ""}
                    onClick={() => setFilter(c)}
                  >
                    {c}
                  </Button>
                ))}
              </div>
              <span className="count-label">{files.length} TÀI LIỆU</span>
            </div>
            <Card>
              {files.filter(
                (f) => filter === "Tất cả môn học" || f.course === filter,
              ).length ? (
                <div className="materials-list">
                  {files
                    .filter(
                      (f) => filter === "Tất cả môn học" || f.course === filter,
                    )
                    .map((f, i) => (
                      <div key={i} className="material-row">
                        <span className="course-icon">
                          <FileText aria-hidden="true" size={22} />
                        </span>
                        <div>
                          <strong>{f.name}</strong>
                          <p>{f.status}</p>
                        </div>
                        <Button
                          className="text-button"
                          onClick={() => setModal("manual")}
                        >
                          Thêm ghi chú thủ công{" "}
                          <ArrowRight aria-hidden="true" size={14} />
                        </Button>
                        <Button
                          className="icon-button"
                          aria-label={`Xóa ${f.name}`}
                          onClick={() => setFiles(files.filter((x) => x !== f))}
                        >
                          <X aria-hidden="true" size={16} />
                        </Button>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="empty-state">
                  <span className="empty-icon">
                    <FolderOpen aria-hidden="true" size={29} />
                  </span>
                  <h2>Không gian cho tài liệu môn học của bạn.</h2>
                  <p>
                    Thêm PDF hoặc ghi chú được cấp phép để bắt đầu xây dựng thư
                    viện. Bản thử nghiệm này chỉ hiển thị tên tệp trên máy;
                    không tải lên, trích xuất hoặc lưu tệp.
                  </p>
                  <Button
                    className="secondary"
                    onClick={() => uploadRef.current?.click()}
                  >
                    <Upload aria-hidden="true" size={16} />
                    Chọn tệp
                  </Button>
                  <Button
                    className="text-button"
                    onClick={() => setModal("manual")}
                  >
                    Hoặc thêm ghi chú thủ công{" "}
                    <ArrowRight aria-hidden="true" size={14} />
                  </Button>
                </div>
              )}
            </Card>
            <div className="materials-note">
              <ShieldCheck aria-hidden="true" size={16} />
              <p>
                Chỉ thêm tài liệu bạn được phép sử dụng. Nếu không thể đọc tài
                liệu, hãy thêm ghi chú thủ công thay vì dựa vào bản tóm tắt
                không có căn cứ.
              </p>
            </div>
          </>
        )}
      </main>
      {modal && (
        <Modal
          title={
            {
              task: edit ? "Chỉnh sửa công việc" : "Thêm công việc",
              proposal: "Kế hoạch học được đề xuất",
              availability: "Thời gian rảnh của bạn",
              reflection: "Thời gian nhìn lại",
              submit: "Gửi câu trả lời?",
              notifications: "Thông báo của bạn",
              account: "Không gian của bạn",
              settings: "Cài đặt bản thử nghiệm",
              help: "Một chút hướng dẫn",
              manual: "Thêm ghi chú thủ công",
              deadline: selectedDeadline.title,
            }[modal] || modal
          }
          close={() => setModal("")}
        >
          {modal === "task" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (remaining > effort) {
                  notify(
                    "Thời lượng còn lại không thể lớn hơn thời lượng dự kiến.",
                  )
                  return
                }
                const t = {
                  id: edit?.id || Date.now(),
                  title: name.trim(),
                  course,
                  time: edit?.time || "Chưa xếp lịch",
                  done: edit?.done || false,
                  effort,
                  priority,
                  deadline,
                }
                if (!t.title) return
                setTasks(
                  edit
                    ? tasks.map((x) => (x.id === edit.id ? t : x))
                    : [...tasks, t],
                )
                setModal("")
                notify(
                  "Đã thêm công việc vào dữ liệu mẫu của phiên này. Lịch không đổi.",
                )
              }}
            >
              <label>
                Tên công việc
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Bạn muốn làm gì?"
                />
              </label>
              <div className="form-grid">
                <label>
                  Môn học
                  <select
                    value={course}
                    onChange={(e) => setCourse(e.target.value)}
                  >
                    {["Giải tích", "Kỹ thuật phần mềm", "Mạng máy tính"].map(
                      (c) => (
                        <option key={c}>{c}</option>
                      ),
                    )}
                  </select>
                </label>
                <label>
                  Mức ưu tiên
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    {["Thấp", "Trung bình", "Cao"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Thời lượng dự kiến (phút)
                  <input
                    type="number"
                    min="15"
                    max="480"
                    required
                    value={effort}
                    onChange={(e) => setEffort(+e.target.value)}
                  />
                </label>
                <label>
                  Thời lượng còn lại (phút)
                  <input
                    type="number"
                    min="0"
                    max={effort}
                    required
                    value={remaining}
                    onChange={(e) => setRemaining(+e.target.value)}
                  />
                </label>
              </div>
              <label>
                Hạn chót · ngày địa phương
                <input
                  type="date"
                  required
                  min={demoDate(0)}
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                />
              </label>
              <div className="modal-actions">
                {edit && (
                  <Button
                    type="button"
                    className="danger-text"
                    onClick={() => {
                      setTasks(tasks.filter((t) => t.id !== edit.id))
                      setModal("")
                    }}
                  >
                    Xóa công việc
                  </Button>
                )}
                <Button
                  type="button"
                  className="secondary"
                  onClick={() => setModal("")}
                >
                  Hủy
                </Button>
                <Button className="primary" type="submit">
                  {edit ? "Lưu thay đổi" : "Thêm công việc"}
                </Button>
              </div>
            </form>
          ) : modal === "availability" ? (
            <>
              <p>
                Thời gian học hôm nay đã được sinh viên xác nhận, sau các cam
                kết hiện có.
              </p>
              <label>
                Khoảng thời gian rảnh
                <select
                  value={capacity}
                  onChange={(e) => setCapacity(+e.target.value)}
                >
                  <option value={60}>17:00–18:00 · 60 phút</option>
                  <option value={30}>17:00–17:30 · 30 phút</option>
                  <option value={15}>
                    17:00–17:15 · 15 phút (thời gian hạn chế)
                  </option>
                </select>
              </label>
              <div className="info-banner">
                <CalendarDays aria-hidden="true" size={18} />
                <p>
                  Cam kết đã xác nhận: Họp nhóm, 14:00–15:00. Các khoảng thời
                  gian được đề xuất không được trùng nhau.
                </p>
              </div>
              <Button
                className="primary"
                onClick={() => {
                  setModal("")
                  notify(
                    "Đã cập nhật thời gian rảnh trong bản mẫu. Các buổi học hiện có không thay đổi.",
                  )
                }}
              >
                Xác nhận thời gian rảnh
              </Button>
            </>
          ) : modal === "proposal" ? (
            <>
              <p>
                Đây là đề xuất minh họa trong bộ nhớ. Bản mẫu chỉ kiểm tra thời
                lượng rảnh và giờ bắt đầu của các công việc mẫu; chưa kiểm tra
                lịch thực tế hay ghi lên máy chủ.
              </p>
              {plannerSource && (
                <div className="info-banner">
                  <FileText aria-hidden="true" size={18} />
                  <p>
                    Tên tệp được chọn: {plannerSource}. Nội dung tệp chưa được
                    đọc.
                  </p>
                </div>
              )}
              <label>
                Điều chỉnh bằng câu lệnh
                <textarea
                  value={plannerPrompt}
                  onChange={(e) => setPlannerPrompt(e.target.value)}
                  placeholder="Ví dụ: chuyển buổi học sang sáng thứ Bảy..."
                />
              </label>
              <div className="proposal-block">
                <BookOpen aria-hidden="true" size={22} />
                <div>
                  <strong>Đạo hàm riêng · Giải tích</strong>
                  <p>
                    {weekDays[0].toLocaleDateString("vi-VN", {
                      weekday: "long",
                      day: "numeric",
                      month: "long",
                    })}{" "}
                    · 17:00–
                    {proposalDuration === 30 ? "17:30" : "18:00"}
                  </p>
                </div>
                <span className="quiet-badge">ĐỀ XUẤT</span>
              </div>
              <label>
                Thời lượng học
                <select
                  value={proposalDuration}
                  onChange={(e) => setProposalDuration(+e.target.value)}
                >
                  <option value={30}>30 phút</option>
                  <option value={60}>60 phút</option>
                </select>
              </label>
              {capacity < proposalDuration ||
              tasks.some((t) => t.time.startsWith("17:00")) ? (
                <div className="warning-banner">
                  <AlertTriangle aria-hidden="true" size={19} />
                  <div>
                    <strong>
                      Chưa xếp lịch:{" "}
                      {capacity < proposalDuration
                        ? "không đủ thời gian rảnh"
                        : "trùng với cam kết khác"}
                    </strong>
                    <p>
                      {capacity < proposalDuration
                        ? `${proposalDuration} phút cần thiết, ${capacity} phút còn trống.`
                        : "Một khoảng thời gian đã xác nhận bắt đầu lúc 17:00."}{" "}
                      Hãy điều chỉnh thời gian rảnh hoặc giữ công việc này ngoài
                      lịch.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="constraint-list">
                  <span>
                    <Check aria-hidden="true" size={15} />
                    Phù hợp với thời lượng rảnh mẫu
                  </span>
                  <span>
                    <Check aria-hidden="true" size={15} />
                    Trước hạn chót mẫu {displayDemoDate(7)}
                  </span>
                  <span>
                    <Check aria-hidden="true" size={15} />
                    Không trùng giờ bắt đầu trong danh sách mẫu
                  </span>
                </div>
              )}
              <div className="modal-actions">
                <Button className="secondary" onClick={() => setModal("")}>
                  Từ chối
                </Button>
                <Button
                  className="text-button"
                  onClick={() => setModal("availability")}
                >
                  Chỉnh sửa thời gian rảnh
                </Button>
                <Button
                  className="primary"
                  disabled={
                    capacity < proposalDuration ||
                    tasks.some((t) => t.time.startsWith("17:00"))
                  }
                  onClick={() => {
                    setTasks([
                      ...tasks,
                      {
                        id: Date.now(),
                        title: "Ôn tập đạo hàm riêng",
                        course: "Giải tích",
                        time: `17:00 – ${
                          proposalDuration === 30 ? "17:30" : "18:00"
                        }`,
                        done: false,
                        effort: proposalDuration,
                        priority: "Trung bình",
                        deadline: demoDate(7),
                      },
                    ])
                    setRevision(false)
                    setModal("")
                    notify(
                      "Đã thêm đề xuất vào dữ liệu mẫu của phiên này. Chưa lưu lên máy chủ.",
                    )
                  }}
                >
                  Xác nhận kế hoạch
                </Button>
              </div>
            </>
          ) : modal === "reflection" ? (
            <>
              <p>
                Xác nhận nội dung bạn đã học. Hoàn thành hoạt động không phải
                bằng chứng về mức độ thành thạo.
              </p>
              <div className="reflection-summary">
                <CheckCheck aria-hidden="true" size={18} />
                <div>
                  <strong>Đã ôn tập đạo hàm riêng</strong>
                  <p>
                    {Math.floor(seconds / 60)} phút hoạt động trong buổi học ·
                    Giải tích
                  </p>
                </div>
              </div>
              <label>
                Phản hồi của bạn
                <textarea
                  value={reflection}
                  onChange={(e) => setReflection(e.target.value)}
                  placeholder="Bạn đã học nội dung gì? Bạn muốn xem lại điều gì?"
                />
              </label>
              <Button
                className="primary"
                onClick={() => {
                  setSessionSaved(true)
                  setModal("")
                  notify("Đã xác nhận kết quả buổi học cho bản minh họa này.")
                }}
              >
                Xác nhận kết quả buổi học
              </Button>
            </>
          ) : modal === "submit" ? (
            <>
              <p>
                Bạn đã chọn <strong>{answer}</strong>. Gửi để xem kết quả cố
                định của câu hỏi mẫu do tác giả biên soạn?
              </p>
              <div className="modal-actions">
                <Button className="secondary" onClick={() => setModal("")}>
                  Tiếp tục xem lại
                </Button>
                <Button
                  className="primary"
                  onClick={() => {
                    setQuizState("results")
                    setModal("")
                  }}
                >
                  Gửi đáp án
                </Button>
              </div>
            </>
          ) : modal === "manual" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const data = new FormData(e.currentTarget)
                setFiles([
                  ...files,
                  {
                    name: String(data.get("title")),
                    course: "Giải tích",
                    status:
                      "Ghi chú thủ công · chưa xác minh · bản minh họa cục bộ",
                  },
                ])
                setModal("")
                notify("Đã thêm tên ghi chú vào thư viện mẫu của phiên này.")
              }}
            >
              <p>
                Đây là lựa chọn thay thế khi không thể xử lý tài liệu. Ghi chú
                chưa được xác minh.
              </p>
              <label>
                Tên ghi chú
                <input
                  name="title"
                  required
                  placeholder="Ví dụ: Bài giảng Giải tích, Chương 3"
                />
              </label>
              <label>
                Nội dung ghi chú
                <textarea
                  required
                  name="note"
                  placeholder="Dán đoạn nội dung bạn được phép sử dụng..."
                />
              </label>
              <Button className="primary" type="submit">
                Thêm ghi chú
              </Button>
            </form>
          ) : modal === "settings" ? (
            <>
              <p>
                Xem trạng thái không gian trống dành cho sinh viên mới. Các thay
                đổi trong bản minh họa chỉ là tạm thời và sẽ đặt lại khi tải lại
                trang.
              </p>
              <Button
                className="secondary"
                onClick={() => {
                  setTasks([])
                  go("Dashboard")
                  setModal("")
                }}
              >
                Xem thử không gian trống
              </Button>
            </>
          ) : modal === "notifications" ? (
            <div className="notification-content">
              <Bell aria-hidden="true" size={28} />
              <h3>Bạn đã xem hết thông báo.</h3>
              <p>
                Hạn chót minh họa tiếp theo là Báo cáo dự án, ngày{" "}
                {displayDemoDate(4)}.
              </p>
            </div>
          ) : (
            <>
              <p>
                {modal === "help"
                  ? "Bắt đầu ở Trang chủ để thử trò chuyện, xem dữ liệu mẫu trong Tổng quan, sắp xếp công việc trong Lập kế hoạch và tập trung ở Học tập. Trợ lý chưa kết nối AI hoặc lưu dữ liệu lâu dài."
                  : modal === "account"
                    ? "Sinh viên · Không gian thử nghiệm cá nhân. Không có tài khoản hoặc lưu trữ lâu dài nào được kết nối."
                    : `${selectedDeadline.course} · Hạn chót mẫu ${selectedDeadline.date}. Mở Lập kế hoạch để xem công việc minh họa.`}
              </p>
              <Button className="secondary" onClick={() => setModal("")}>
                Đã hiểu
              </Button>
            </>
          )}
        </Modal>
      )}
      {notice && (
        <div className="toast">
          <span role="status">{notice}</span>
          <Check aria-hidden="true" size={17} />
          <Button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X aria-hidden="true" size={14} />
          </Button>
        </div>
      )}
    </div>
  )
}
