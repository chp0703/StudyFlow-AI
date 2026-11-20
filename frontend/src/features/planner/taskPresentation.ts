const PROVENANCE_LINE = /^(recommendation_id|attempt_ids|chunk_ids):\s*(.+)$/
const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export type TaskDescriptionPresentation = {
  summary: string
  original: string
  isRevision: boolean
}

export function presentTaskDescription(
  description: string | null | undefined,
): TaskDescriptionPresentation | null {
  if (!description) return null

  const lines = description.split("\n")
  const metadata = new Map<string, string[]>()
  let firstMetadata = lines.length

  lines.forEach((line, index) => {
    const match = line.trim().match(PROVENANCE_LINE)
    if (!match) return
    firstMetadata = Math.min(firstMetadata, index)
    metadata.set(
      match[1],
      match[2]
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    )
  })

  const recommendationIds = metadata.get("recommendation_id")
  const attemptIds = metadata.get("attempt_ids")
  const chunkIds = metadata.get("chunk_ids")
  const recognized =
    recommendationIds?.length === 1 &&
    recommendationIds.every((id) => UUID.test(id)) &&
    Boolean(attemptIds?.length || chunkIds?.length) &&
    [...(attemptIds ?? []), ...(chunkIds ?? [])].every((id) => UUID.test(id)) &&
    lines
      .slice(firstMetadata)
      .every((line) => !line.trim() || PROVENANCE_LINE.test(line.trim()))

  return {
    summary: recognized
      ? lines.slice(0, firstMetadata).join("\n").trim()
      : description,
    original: description,
    isRevision: Boolean(recognized),
  }
}
