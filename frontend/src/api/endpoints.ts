import type { ApiClient } from "./client.ts"

import type {
  ActionReference,
  ApiTask,
  ApiTimeWindow,
  ListResult,
  OrchestratorReply,
  PlanProposal,
  PlanView,
  IngestionSource,
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

    sendMessage: (conversationId: string, text: string, key?: string, sourceIds?: string[]) =>
      client.request<OrchestratorReply>("POST", "/v1/messages", {
        body: {
          schema_version: SCHEMA,
          conversation_id: conversationId,
          text,
          ...(sourceIds?.length ? { source_ids: sourceIds } : {}),
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
