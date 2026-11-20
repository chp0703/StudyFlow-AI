export function composerKeyAction({
  key,
  shiftKey,
  isComposing,
  busy,
  hasText,
}: {
  key: string
  shiftKey: boolean
  isComposing: boolean
  busy: boolean
  hasText: boolean
}) {
  if (key === "Escape" && !hasText) return "collapse"
  if (key === "Enter" && !shiftKey && !isComposing && !busy && hasText)
    return "submit"
  return "none"
}
