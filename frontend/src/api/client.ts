import type { ApiErrorBody } from "./types.ts"

export class ApiError extends Error {
  code: string

  status: number

  retryable: boolean

  field: string | null

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)

    this.code = body.code

    this.status = status

    this.retryable = body.retryable

    this.field = body.field
  }
}

type Query = Record<string, string | number | boolean | string[] | null | undefined>

export type ClientOptions = {
  baseUrl: string

  getToken: () => Promise<string | null>

  onUnauthenticated?: () => void

  fetchImpl?: typeof fetch

  retryDelayMs?: number
}

export type RequestOptions = {
  query?: Query

  body?: unknown

  // POST only. Reuse the same key when the user retries the same action.
  idempotencyKey?: string
}

function queryString(query: Query | undefined): string {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null) continue

    for (const item of Array.isArray(value) ? value : [value])
      params.append(key, String(item))
  }

  const text = params.toString()

  return text ? `?${text}` : ""
}

const NETWORK_ERROR: ApiErrorBody = {
  code: "SERVICE_UNAVAILABLE",

  message: "Không kết nối được máy chủ.",

  field: null,

  retryable: true,
}

// Thin fetch wrapper: bearer token, idempotency key, catalog errors, one retry of a transient failure.
export function createApiClient(options: ClientOptions) {
  const doFetch = options.fetchImpl ?? ((...args) => fetch(...args))

  async function once(method: string, path: string, opts: RequestOptions) {
    const token = await options.getToken()

    if (!token) {
      options.onUnauthenticated?.()

      throw new ApiError(401, {
        code: "UNAUTHENTICATED",
        message: "Cần đăng nhập.",
        field: null,
        retryable: false,
      })
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
    }

    if (method === "POST") {
      headers["Content-Type"] = "application/json"

      headers["Idempotency-Key"] = opts.idempotencyKey ?? crypto.randomUUID()
    }

    let response: Response

    try {
      response = await doFetch(
        `${options.baseUrl}${path}${queryString(opts.query)}`,
        {
          method,
          headers,
          body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        },
      )
    } catch {
      throw new ApiError(0, NETWORK_ERROR)
    }

    let json: unknown

    try {
      json = await response.json()
    } catch {
      json = null
    }

    if (response.ok) return json

    const error = (json as { error?: ApiErrorBody } | null)?.error

    if (response.status === 401) options.onUnauthenticated?.()

    throw new ApiError(
      response.status,
      error ?? { ...NETWORK_ERROR, retryable: response.status >= 500 },
    )
  }

  async function request<T>(
    method: "GET" | "POST",
    path: string,
    opts: RequestOptions = {},
  ): Promise<T> {
    // A POST without a key would not be safe to repeat, so fix one before the first attempt.
    const fixed =
      method === "POST" && !opts.idempotencyKey
        ? { ...opts, idempotencyKey: crypto.randomUUID() }
        : opts

    try {
      return (await once(method, path, fixed)) as T
    } catch (error) {
      if (!(error instanceof ApiError) || !error.retryable) throw error

      await new Promise((r) => setTimeout(r, options.retryDelayMs ?? 400))

      return (await once(method, path, fixed)) as T
    }
  }

  return { request }
}

export type ApiClient = ReturnType<typeof createApiClient>

const MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.",

  SERVICE_UNAVAILABLE: "Dịch vụ tạm thời chưa sẵn sàng. Hãy thử lại sau.",

  INTERNAL_ERROR: "Có lỗi xảy ra. Hãy thử lại sau.",

  INVALID_PARAMETER: "Dữ liệu chưa hợp lệ.",

  STALE_PROPOSAL:
    "Lịch đã thay đổi từ lúc tạo đề xuất. Hãy từ chối và tạo lại.",

  STALE_PLAN_VERSION: "Kế hoạch hiện tại đã thay đổi. Hãy tạo lại đề xuất.",

  STALE_ENTITY_VERSION: "Nội dung đã thay đổi. Hãy tải lại rồi thử lại.",

  ACTION_REVIEW_REQUIRED:
    "Đang có thao tác chờ xác nhận. Hãy xác nhận hoặc hủy trước.",

  ENTITY_NOT_FOUND: "Không tìm thấy nội dung này.",

  IDEMPOTENCY_CONFLICT: "Yêu cầu này đã được gửi với nội dung khác.",

  TIME_CONFLICT: "Lịch học bị trùng giờ.",

  UNSUPPORTED_OPERATION: "Yêu cầu này chưa được hỗ trợ.",

  APPROVAL_REQUIRED: "Cần xác nhận trước khi thực hiện.",

  RATE_LIMITED: "Bạn thao tác quá nhanh. Hãy thử lại sau ít phút.",

  PAYLOAD_TOO_LARGE: "Nội dung quá dài.",
}

// Vietnamese text for an error; the server message is used when it is already user-facing.
export function errorText(error: unknown): string {
  if (error instanceof ApiError)
    return MESSAGES[error.code] ?? error.message ?? MESSAGES.INTERNAL_ERROR

  return MESSAGES.INTERNAL_ERROR
}
