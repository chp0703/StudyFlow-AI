export function resizePlannerComposer(textarea: HTMLTextAreaElement) {
  textarea.style.height = "auto"
  textarea.style.height = `${Math.min(textarea.scrollHeight, 112)}px`
  textarea.style.overflowY = textarea.scrollHeight > 112 ? "auto" : "hidden"
}
