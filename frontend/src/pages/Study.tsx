import { useEffect, useState } from "react"
import { BrainCircuit, Sparkles } from "lucide-react"
import { apiEnabled } from "../api/config"
import type { ApiTask } from "../api/types"
import AssessmentWorkspace from "../features/assessment/AssessmentWorkspace"
import DemoQuiz from "../features/assessment/DemoQuiz"
import DailyLearningWorkspace from "../features/learning/DailyLearningWorkspace"
import DemoLearningWorkspace from "../features/learning/DemoLearningWorkspace"
import type { RevisionSchedulingState } from "../features/planner/revisionScheduling"

type StudyArea = "assessment" | "learning"

export default function Study({
  userId,
  plannerBlockId,
  plannerGoal,
  revisionScheduling,
  onRevisionTaskConfirmed,
  onOpenPlanner,
  onRetryScheduling,
}: {
  userId: string
  plannerBlockId?: string | null
  plannerGoal?: string
  revisionScheduling?: RevisionSchedulingState | null
  onRevisionTaskConfirmed?: (task: ApiTask) => void
  onOpenPlanner?: () => void
  onRetryScheduling?: () => void
}) {
  const [area, setArea] = useState<StudyArea>(
    plannerBlockId ? "learning" : "assessment",
  )

  useEffect(() => {
    if (plannerBlockId) setArea("learning")
  }, [plannerBlockId])

  return (
    <div className="study-hub">
      <div
        className="study-area-tabs"
        role="tablist"
        aria-label="Khu vực học tập"
      >
        <button
          type="button"
          role="tab"
          aria-selected={area === "assessment"}
          className={area === "assessment" ? "is-active" : ""}
          onClick={() => setArea("assessment")}
        >
          <BrainCircuit size={17} aria-hidden="true" />
          Đánh giá kiến thức
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={area === "learning"}
          className={area === "learning" ? "is-active" : ""}
          onClick={() => setArea("learning")}
        >
          <Sparkles size={17} aria-hidden="true" />
          Học cùng AI
        </button>
      </div>
      <section
        className="study-area-panel"
        role="tabpanel"
        hidden={area !== "assessment"}
      >
        {apiEnabled ? (
          <div className="study-container study-assessment-container">
            <AssessmentWorkspace
              revisionScheduling={revisionScheduling}
              onRevisionTaskConfirmed={onRevisionTaskConfirmed}
              onOpenPlanner={onOpenPlanner}
              onRetryScheduling={onRetryScheduling}
            />
          </div>
        ) : (
          <div className="study-container study-demo-assessment">
            <DemoQuiz />
          </div>
        )}
      </section>
      <section
        className="study-area-panel"
        role="tabpanel"
        hidden={area !== "learning"}
      >
        {apiEnabled ? (
          <DailyLearningWorkspace
            userId={userId}
            plannerBlockId={plannerBlockId ?? null}
            initialGoal={plannerGoal ?? ""}
          />
        ) : (
          <DemoLearningWorkspace />
        )}
      </section>
    </div>
  )
}
