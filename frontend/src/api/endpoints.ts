import type { ApiClient } from "./client.ts"

import type {
  ActionReference,
  ApiTask,
  ApiTimeWindow,
  AssessmentMaterialDetailData,
  IngestionSource,
  ListResult,
  OrchestratorReply,
  PlanProposal,
  PlanView,
  QuestionDraft,
  QuestionDraftStatus,
  QuestionType,
  QuizAttempt,
  QuizAttemptOrigin,
  QuizAttemptSubmissionData,
  QuizResponse,
  TopicStatsData,
} from "./types.ts"

type Read<T> = { data: T }

const SCHEMA = "1.1"

// One function per endpoint of contracts/openapi.yaml; the screens never build URLs themselves.
export function createEndpoints(client: ApiClient) {
  async function allPages<T>(
    path: string,
    query: Record<string, string | number | boolean | undefined>,
  ): Promise<T[]> {
    const items: T[] = []

    let cursor: string | undefined

    for (;;) {
      const page = await client.request<ListResult<T>>("GET", path, {
        query: { ...query, page_size: 100, cursor },
      })

      items.push(...page.data.items)

      if (!page.data.next_cursor) return items

      cursor = page.data.next_cursor
    }
  }

  return {
    listTasks: () => allPages<ApiTask>("/v1/tasks", {}),

    listTimeWindows: () => allPages<ApiTimeWindow>("/v1/time-windows", {}),

    getPreferences: () =>
      client.request<Read<{
        scheduling_policy: Record<string, unknown>
        schedule_revision: number
      }>>("GET", "/v1/preferences"),

    getCurrentPlan: () =>
      client
        .request<Read<PlanView>>("GET", "/v1/plans", {
          query: { view: "CURRENT" },
        })
        .then((r) => r.data),

    getProposal: (proposalId: string) =>
      client
        .request<Read<{ proposal: PlanProposal }>>("GET", "/v1/plans", {
          query: { view: "PROPOSAL", proposal_id: proposalId },
        })
        .then((r) => r.data.proposal),

    uploadSource: (conversationId: string, filename: string, mimeType: string, contentBase64: string, key?: string) =>
      client.request<Read<IngestionSource>>("POST", "/v1/sources", {
        body: { schema_version: SCHEMA, conversation_id: conversationId, filename, mime_type: mimeType, content_base64: contentBase64 },
        idempotencyKey: key,
      }),

    getSource: (conversationId: string, sourceId: string) =>
      client.request<Read<IngestionSource>>("GET", `/v1/sources/${encodeURIComponent(sourceId)}`, {
        query: { conversation_id: conversationId },
      }),

    extractSource: (conversationId: string, sourceId: string, key?: string) =>
      client.request<Read<IngestionSource>>("POST", `/v1/sources/${encodeURIComponent(sourceId)}/extract`, {
        body: { schema_version: SCHEMA, conversation_id: conversationId },
        idempotencyKey: key,
      }),

    uploadAssessmentMaterial: (
      conversationId: string,
      filename: string,
      mimeType: "text/plain" | "text/markdown" | "application/pdf",
      contentBase64: string,
      topics: string[],
      key?: string,
    ) =>
      client.request<Read<AssessmentMaterialDetailData>>("POST", "/v1/assessment/materials", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          filename,
          mime_type: mimeType,
          content_base64: contentBase64,
          topics,
        },
        idempotencyKey: key,
      }),

    getAssessmentMaterial: (conversationId: string, materialId: string) =>
      client.request<Read<AssessmentMaterialDetailData>>(
        "GET",
        `/v1/assessment/materials/${encodeURIComponent(materialId)}`,
        {
          query: { conversation_id: conversationId },
        },
      ),

    generateQuestionDrafts: (
      conversationId: string,
      materialId: string,
      topic: string,
      questionType: QuestionType,
      count: number,
      key?: string,
    ) =>
      client.request<OrchestratorReply>("POST", "/v1/assessment/drafts", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          material_id: materialId,
          topic,
          question_type: questionType,
          count,
        },
        idempotencyKey: key,
      }),

    listAssessmentQuestions: (
      filters: {
        material_id?: string
        topic?: string
        status?: QuestionDraftStatus
      } = {},
    ) => allPages<QuestionDraft>("/v1/assessment/questions", filters),

    createQuizAttempt: (
      materialId: string,
      questionIds: string[],
      origin: QuizAttemptOrigin = "MANUAL",
      sessionOutcomeId: string | null = null,
      key?: string,
    ) =>
      client.request<Read<QuizAttempt>>("POST", "/v1/assessment/attempts", {
        body: {
          schema_version: SCHEMA,
          material_id: materialId,
          question_ids: questionIds,
          origin,
          session_outcome_id: sessionOutcomeId,
        },
        idempotencyKey: key,
      }),

    saveQuizResponse: (
      attemptId: string,
      questionId: string,
      selectedOptionId: string | null,
      key?: string,
    ) =>
      client.request<Read<QuizResponse>>(
        "PUT",
        `/v1/assessment/attempts/${encodeURIComponent(attemptId)}/responses/${encodeURIComponent(questionId)}`,
        {
          body: {
            schema_version: SCHEMA,
            selected_option_id: selectedOptionId,
          },
          idempotencyKey: key,
        },
      ),

    submitQuizAttempt: (attemptId: string, key?: string) =>
      client.request<Read<QuizAttemptSubmissionData>>(
        "POST",
        `/v1/assessment/attempts/${encodeURIComponent(attemptId)}/submit`,
        {
          body: { schema_version: SCHEMA },
          idempotencyKey: key,
        },
      ),

    getTopicStats: (materialId?: string) =>
      client.request<Read<TopicStatsData>>("GET", "/v1/assessment/topics/stats", {
        query: materialId ? { material_id: materialId } : {},
      }),

    createRevisionRecommendation: (
      conversationId: string,
      materialId: string,
      topic: string,
      suggestedMinutes: number,
      priority: 0.1 | 0.5 | 1,
      key?: string,
    ) =>
      client.request<OrchestratorReply>("POST", "/v1/assessment/recommendations", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          material_id: materialId,
          topic,
          suggested_minutes: suggestedMinutes,
          priority,
        },
        idempotencyKey: key,
      }),

    sendMessage: (conversationId: string, text: string = "", key?: string, sourceIds?: string[]) =>
      client.request<OrchestratorReply>("POST", "/v1/messages", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          text,
          ...(sourceIds?.length ? { source_ids: sourceIds } : {}),
        },
        idempotencyKey: key,
      }),

    prepareAvailability: (
      conversationId: string,
      arguments_: {
        change_type: "ADD" | "UPDATE" | "ARCHIVE"
        window_id: string | null
        expected_window_version: number | null
        window: Omit<ApiTimeWindow, "window_id" | "version" | "archived_at"> | null
      },
      key?: string,
    ) =>
      client.request<OrchestratorReply>("POST", "/v1/actions", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          operation: "set_availability",
          arguments: arguments_,
        },
        idempotencyKey: key,
      }),

    decide: (
      conversationId: string,
      reference: ActionReference,
      decision: "APPROVE" | "REJECT",
      key?: string,
    ) =>
      client.request<OrchestratorReply>("POST", "/v1/decisions", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          action_reference: reference,
          decision,
        },
        idempotencyKey: key,
      }),

    reviewAction: (
      conversationId: string,
      actionId: string,
      expectedVersion: number,
      key?: string,
    ) =>
      client.request<OrchestratorReply>(
        "POST",
        `/v1/actions/${actionId}/review`,
        {
          body: {
            schema_version: SCHEMA,
            conversation_id: conversationId,
            expected_action_version: expectedVersion,
          },
          idempotencyKey: key,
        },
      ),
  }
}

export type Endpoints = ReturnType<typeof createEndpoints>
