import { useCallback, useEffect, useRef, useState } from "react"

import { api } from "./index"

import { errorText } from "./client"

import { expandWindows, mapTasksAndEvents } from "./mappers"

import type { TimeWindow } from "../types/planner"

import type { Task } from "../types/task"
import type { ApiTimeWindow } from "./types"
import { addCivilDays, vietnamDate } from "../utils/date"

// The calendar shows cells from two weeks back to about ten weeks ahead.
const WINDOW_DAYS = 84

const WINDOW_BACK_DAYS = 14

export type ServerData = {
  tasks: Task[]

  // One calendar event per study block of the current plan.
  events: Task[]

  availability: TimeWindow[]

  windows: ApiTimeWindow[]

  revision: number

  loading: boolean

  error: string

  reload: () => Promise<void>
}

// Everything the screens read from the API; `reload` is called after anything that may have changed it.
export function useServerData(enabled: boolean, userId?: string): ServerData {
  const activeUserId = useRef(userId)
  activeUserId.current = userId
  const [state, setState] = useState({
    tasks: [] as Task[],

    events: [] as Task[],

    availability: [] as TimeWindow[],

    windows: [] as ApiTimeWindow[],

    revision: 0,
  })

  const [loading, setLoading] = useState(enabled)

  const [error, setError] = useState("")

  const reload = useCallback(async () => {
    if (!enabled) return

    try {
      const [tasks, windows, plan, preferences] = await Promise.all([
        api.listTasks(),

        api.listTimeWindows(),

        api.getCurrentPlan(),

        api.getPreferences(),
      ])
      if (activeUserId.current !== userId) return

      const from = new Date(
        `${addCivilDays(vietnamDate(), -WINDOW_BACK_DAYS)}T12:00:00Z`,
      )

      setState({
        ...mapTasksAndEvents(tasks, plan.study_blocks),

        availability: expandWindows(windows, from, WINDOW_DAYS),

        windows,

        revision: preferences.data.schedule_revision,
      })

      setError("")
    } catch (e) {
      if (activeUserId.current === userId) setError(errorText(e))
    } finally {
      if (activeUserId.current === userId) setLoading(false)
    }
  }, [enabled, userId])

  useEffect(() => {
    // A new session starts from a clean slate so one account never shows another's data.
    setState({
      tasks: [],
      events: [],
      availability: [],
      windows: [],
      revision: 0,
    })

    void reload()
  }, [reload])

  return { ...state, loading, error, reload }
}
