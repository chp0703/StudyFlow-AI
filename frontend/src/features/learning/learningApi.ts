import { ApiError, errorText } from "../../api/client.ts"
import type {
  DailyLearningCitation,
  DailyLearningMaterial,
  DailyLearningTurn,
  DailyMaterialStatus,
} from "../../api/types.ts"

export const MAX_MATERIAL_BYTES = 5 * 1024 * 1024
export const MAX_SELECTED_MATERIALS = 5
export const POLL_INTERVAL_MS = 2000

const MIME_BY_EXTENSION: Record<string, DailyLearningMaterial["mime_type"]> = {
  pdf: "application/pdf",
  txt: "text/plain",
  md: "text/markdown",
}

export type CitationView = DailyLearningCitation & { label: string }
export type LearningTurnView = Omit<DailyLearningTurn, "citations"> & {
  citations: CitationView[]
}

export function materialMime(file: Pick<File, "name" | "type">) {
  const extension = file.name.toLocaleLowerCase("vi").split(".").pop() ?? ""
  return MIME_BY_EXTENSION[extension] ?? null
}

export function validateMaterialFile(
  file: Pick<File, "name" | "size" | "type">,
): string | null {
  if (!materialMime(file)) return "Chỉ hỗ trợ tệp PDF, TXT hoặc Markdown."
  if (!file.size) return "Tệp đang trống. Hãy chọn một tệp có nội dung."
  if (file.size > MAX_MATERIAL_BYTES) return "Tệp không được vượt quá 5 MiB."
  return null
}

export function readFileBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error("Không đọc được tệp đã chọn."))
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "")
    reader.readAsDataURL(file)
  })
}

export function materialStatus(status: DailyMaterialStatus) {
  switch (status) {
    case "UPLOADED":
      return { label: "Đã nhận tệp", tone: "pending" as const, polling: true }
    case "INDEXING":
      return {
        label: "Đang lập chỉ mục…",
        tone: "pending" as const,
        polling: true,
      }
    case "READY":
      return { label: "Sẵn sàng", tone: "ready" as const, polling: false }
    case "FAILED":
      return {
        label: "Lập chỉ mục thất bại",
        tone: "failed" as const,
        polling: false,
      }
  }
}

export function formatMaterialError(material: DailyLearningMaterial) {
  if (material.error_code === "INVALID_DOCUMENT")
    return "Tài liệu không hợp lệ, bị quét ảnh hoặc vượt quá 50 trang."
  if (material.error_code === "INDEX_TIMEOUT")
    return "Lập chỉ mục quá thời gian. Hãy tải lại tài liệu."
  if (material.error_code === "INDEX_UNAVAILABLE")
    return "Dịch vụ lập chỉ mục tạm thời không khả dụng."
  return "Không thể lập chỉ mục tài liệu này."
}

export function learningError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 413) return "Tệp không được vượt quá 5 MiB."
    if (error.status === 415) return "Định dạng tài liệu chưa được hỗ trợ."
    if (error.status === 503)
      return "Trợ lý AI tạm thời không khả dụng. Hãy thử lại sau."
  }
  return error instanceof Error ? error.message : errorText(error)
}

export function mapLearningTurn(
  turn: DailyLearningTurn,
  materials: ReadonlyMap<string, DailyLearningMaterial>,
): LearningTurnView {
  const citations = turn.citations.map((citation) => {
    const material = materials.get(citation.material_id)
    const label = citation.material_deleted
      ? "Tài liệu đã xoá"
      : `${material?.filename ?? "Tài liệu"} · tr. ${citation.page}`
    return { ...citation, label }
  })
  return { ...turn, citations }
}

export function formatBytes(bytes: number) {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MiB`
    : `${Math.max(1, Math.round(bytes / 1024))} KiB`
}
