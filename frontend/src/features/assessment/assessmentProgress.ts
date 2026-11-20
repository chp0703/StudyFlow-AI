export type AssessmentStage = "materials" | "questions" | "practice" | "results"

export type AssessmentStageState = Record<AssessmentStage, {
  available: boolean
  completed: boolean
}>

export function assessmentStageState({
  materialReady,
  verifiedCount,
  hasAttempt,
  hasResult,
  statsLoaded,
}: {
  materialReady: boolean
  verifiedCount: number
  hasAttempt: boolean
  hasResult: boolean
  statsLoaded: boolean
}): AssessmentStageState {
  return {
    materials: { available: true, completed: materialReady },
    questions: { available: materialReady, completed: verifiedCount > 0 },
    practice: {
      available: verifiedCount > 0 || hasAttempt,
      completed: hasResult,
    },
    results: {
      available: materialReady,
      completed: statsLoaded,
    },
  }
}
