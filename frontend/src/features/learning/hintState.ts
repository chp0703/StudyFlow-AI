export type HintState = {
  level: 0 | 1 | 2 | 3
  exhausted: boolean
  valid: boolean
}

export const initialHintState = (): HintState => ({
  level: 0,
  exhausted: false,
  valid: true,
})

export const resetHintState = () => initialHintState()

export function applyServerHintLevel(
  current: HintState,
  serverLevel: number | null,
): HintState {
  if (
    !Number.isInteger(serverLevel) ||
    serverLevel === null ||
    serverLevel < 1 ||
    serverLevel > 3 ||
    serverLevel < current.level
  )
    return { ...current, valid: false }
  const level = serverLevel as 1 | 2 | 3
  return { level, exhausted: level === 3, valid: true }
}

export const hintButtonLabel = (state: HintState) =>
  state.exhausted ? "Đã dùng 3/3 gợi ý" : `Gợi ý ${state.level + 1}/3`
