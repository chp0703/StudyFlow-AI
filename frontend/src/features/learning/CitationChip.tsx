import { FileText } from "lucide-react"
import type { CitationView } from "./learningApi"

export default function CitationChip({ citation }: { citation: CitationView }) {
  return (
    <span
      className="learning-citation-chip"
      aria-label={`Nguồn: ${citation.label}`}
      title={citation.label}
    >
      <FileText size={13} aria-hidden="true" />
      {citation.label}
    </span>
  )
}
