export type IntentCandidate = "CREATE_TASK" | "UPDATE_TASK" | "DELETE_TASK" | "SET_AVAILABILITY" | "GENERATE_STUDY_PLAN" | "RESCHEDULE_STUDY_BLOCK" | "GET_STUDY_PLAN" | "CREATE_STUDY_BLOCK"

export type ResponseCategory = "MESSAGE" | "CLARIFICATION" | "PROPOSAL" | "UNSUPPORTED" | "ERROR"
export type ApprovalStatus = "awaiting_approval" | "cancelled" | "demo_acknowledged"
export type DemoScenario = "task" | "plan" | "view" | "reschedule"
export type ValidationState = "missing_information" | "valid_demo_draft"

export type ActionProposal = {
  intent: IntentCandidate
  title: string
  details: {
    label: string
    value: string
  }[]
  caveat: string
  status: ApprovalStatus
}

export type ChatMessage = {
  id: number
  role: "user" | "assistant"
  category: ResponseCategory
  text: string
  scenario?: DemoScenario
  intent?: IntentCandidate
  validation?: ValidationState
  proposal?: ActionProposal
  error?: {
    code: string
    detail: string
  }
}

export const suggestions: {
  scenario: DemoScenario
  title: string
  prompt: string
}[] = [
  {
    scenario: "task",
    title: "Thêm công việc mới",
    prompt: "Tạo task làm bài OOP.",
  },
  {
    scenario: "plan",
    title: "Lập kế hoạch học tập",
    prompt: "Lập kế hoạch học tập cho tôi.",
  },
  { scenario: "view", title: "Xem lịch học", prompt: "Xem lịch học hiện tại." },
  {
    scenario: "reschedule",
    title: "Điều chỉnh buổi học",
    prompt: "Điều chỉnh buổi học.",
  },
]

// This deliberately recognizes only four demo entry points. It is not an NLP or API client.
export function demoReply(input: string): Omit<ChatMessage, "id"> {
  const value = input.trim().toLocaleLowerCase("vi")
  if (/^(tạo task|thêm công việc)/u.test(value)) {
    return {
      role: "assistant",
      category: "CLARIFICATION",
      scenario: "task",
      intent: "CREATE_TASK",
      validation: "missing_information",
      text: "Mình có thể giúp bạn phác thảo công việc. Vui lòng điền các thông tin còn thiếu; bản mẫu sẽ không lưu công việc vào hệ thống.",
    }
  }
  if (/^(lập kế hoạch|tạo kế hoạch)/u.test(value)) {
    return {
      role: "assistant",
      category: "CLARIFICATION",
      scenario: "plan",
      intent: "GENERATE_STUDY_PLAN",
      validation: "missing_information",
      text: "Để phác thảo kế hoạch, cần biết công việc, hạn hoàn thành và thời gian bạn có thể học. Ví dụ này chưa kiểm tra lịch bận hay ràng buộc thực tế.",
    }
  }
  if (/^(xem lịch|xem kế hoạch)/u.test(value)) {
    return {
      role: "assistant",
      category: "MESSAGE",
      scenario: "view",
      intent: "GET_STUDY_PLAN",
      text: "Bạn có thể mở trang Lập kế hoạch để xem lịch minh họa đang có trong ứng dụng. Dữ liệu ở đó là dữ liệu mẫu.",
    }
  }
  if (/^(điều chỉnh|đổi lịch|dời lịch)/u.test(value)) {
    return {
      role: "assistant",
      category: "CLARIFICATION",
      scenario: "reschedule",
      intent: "RESCHEDULE_STUDY_BLOCK",
      validation: "missing_information",
      text: "Bạn muốn điều chỉnh buổi học nào và sang thời điểm nào? Mẫu này chỉ tạo đề xuất, không thay đổi lịch hiện có.",
    }
  }
  return {
    role: "assistant",
    category: "UNSUPPORTED",
    text: "Bản mẫu hiện hỗ trợ bốn luồng ở trên. Hãy chọn một gợi ý để xem cách tạo công việc, phác thảo kế hoạch, xem lịch mẫu hoặc điều chỉnh buổi học. Tin nhắn này chưa được gửi tới AI.",
  }
}
