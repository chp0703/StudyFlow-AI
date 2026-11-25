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
  onAreaChange,
}: {
  userId: string
  plannerBlockId?: string | null
  plannerGoal?: string
  revisionScheduling?: RevisionSchedulingState | null
  onRevisionTaskConfirmed?: (task: ApiTask) => void
  onOpenPlanner?: () => void
  onRetryScheduling?: () => void
  onAreaChange?: (area: StudyArea) => void
}) {
  const [area, setArea] = useState<StudyArea>(
    plannerBlockId ? "learning" : "assessment",
  )

  useEffect(() => {
    if (plannerBlockId) setArea("learning")
  }, [plannerBlockId])

  useEffect(() => {
    onAreaChange?.(area)
  }, [area, onAreaChange])

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
          aria-controls="study-assessment-panel"
          id="study-assessment-tab"
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
          aria-controls="study-learning-panel"
          id="study-learning-tab"
          className={area === "learning" ? "is-active" : ""}
          onClick={() => setArea("learning")}
        >
          <Sparkles size={17} aria-hidden="true" />
          Học cùng AI
        </button>
      </div>
      <section
        id="study-assessment-panel"
        className="study-area-panel"
        role="tabpanel"
        aria-labelledby="study-assessment-tab"
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
        id="study-learning-panel"
        className="study-area-panel"
        role="tabpanel"
        aria-labelledby="study-learning-tab"
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
