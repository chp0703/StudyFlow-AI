import { useCallback, useState } from "react"
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
  const select = useCallback(
    (items: DailyLearningMaterial[]) => setSelected(items),
    [],
  )
  const updateMaterials = useCallback(
    (items: DailyLearningMaterial[]) => setMaterials(items),
    [],
  )
  return (
    <div className="daily-learning-workspace">
      <MaterialsCard
        onSelectionChange={select}
        onMaterialsChange={updateMaterials}
      />
      <LearningSession
        userId={userId}
        selectedMaterials={selected}
        materials={materials}
        plannerBlockId={plannerBlockId}
        initialGoal={initialGoal}
      />
    </div>
  )
}
