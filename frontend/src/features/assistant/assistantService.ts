import type { ChatMessage } from "../../types/assistant"

// This deliberately recognizes only four entry points. It is not an NLP or API client.
export function getAssistantReply(
  input: string,
): Omit<ChatMessage, "id" | "timestamp"> {
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
      text: "Bạn có thể mở trang Lập kế hoạch để xem lịch của bạn.",
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
    text: "Bản mẫu hiện hỗ trợ tạo công việc, phác thảo kế hoạch, xem lịch mẫu và điều chỉnh buổi học. Hãy bắt đầu yêu cầu bằng một trong các cách đó. Tin nhắn này chưa được gửi tới AI.",
  }
}
