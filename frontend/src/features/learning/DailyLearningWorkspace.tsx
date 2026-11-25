import { useCallback, useState } from "react"
import { BookOpen, MessageSquareText } from "lucide-react"
import type { DailyLearningMaterial } from "../../api/types"
import LearningSession from "./LearningSession"
import MaterialsCard from "./MaterialsCard"

export default function DailyLearningWorkspace({
  userId,
  plannerBlockId,
  initialGoal,
}: {
  userId: string
  plannerBlockId: string | null
  initialGoal: string
}) {
  const [selected, setSelected] = useState<DailyLearningMaterial[]>([])
  const [materials, setMaterials] = useState<DailyLearningMaterial[]>([])
  const [mobileView, setMobileView] = useState<"materials" | "session">(
    "session",
  )
  const select = useCallback(
    (items: DailyLearningMaterial[]) => setSelected(items),
    [],
  )
  const updateMaterials = useCallback(
    (items: DailyLearningMaterial[]) => setMaterials(items),
    [],
  )
  return (
    <div className="daily-learning-shell">
      <div
        className="learning-mobile-switcher"
        role="group"
        aria-label="Khu vực phiên học"
      >
        <button
          type="button"
          aria-pressed={mobileView === "materials"}
          onClick={() => setMobileView("materials")}
        >
          <BookOpen size={16} aria-hidden="true" />
          Tài liệu
          {selected.length > 0 && <span>{selected.length}</span>}
        </button>
        <button
          type="button"
          aria-pressed={mobileView === "session"}
          onClick={() => setMobileView("session")}
        >
          <MessageSquareText size={16} aria-hidden="true" />
          Phiên học
        </button>
      </div>
      <div className="daily-learning-workspace">
        <div className={mobileView !== "materials" ? "is-mobile-hidden" : ""}>
          <MaterialsCard
            onSelectionChange={select}
            onMaterialsChange={updateMaterials}
          />
        </div>
        <div className={mobileView !== "session" ? "is-mobile-hidden" : ""}>
          <LearningSession
            userId={userId}
            selectedMaterials={selected}
            materials={materials}
            plannerBlockId={plannerBlockId}
            initialGoal={initialGoal}
          />
        </div>
      </div>
    </div>
  )
}
