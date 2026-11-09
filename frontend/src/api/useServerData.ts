import { useCallback, useEffect, useState } from "react"

import { api } from "./index"

import { errorText } from "./client"

import { expandWindows, mapTasksAndEvents } from "./mappers"

import type { TimeWindow } from "../types/planner"

import type { Task } from "../types/task"

// The calendar shows cells from two weeks back to about ten weeks ahead.
const WINDOW_DAYS = 84

const WINDOW_BACK_DAYS = 14

export type ServerData = {
  tasks: Task[]

  // One calendar event per study block of the current plan.
  events: Task[]

  availability: TimeWindow[]

  revision: number

  loading: boolean

  error: string

  reload: () => Promise<void>
}

// Everything the screens read from the API; `reload` is called after anything that may have changed it.
export function useServerData(enabled: boolean): ServerData {
  const [state, setState] = useState({
    tasks: [] as Task[],

    events: [] as Task[],

    availability: [] as TimeWindow[],

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

      const from = new Date()

      from.setDate(from.getDate() - WINDOW_BACK_DAYS)

      setState({
        ...mapTasksAndEvents(tasks, plan.study_blocks),

        availability: expandWindows(windows, from, WINDOW_DAYS),

        revision: preferences.data.schedule_revision,
      })

      setError("")
    } catch (e) {
      setError(errorText(e))
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    // A new session starts from a clean slate so one account never shows another's data.
    setState({ tasks: [], events: [], availability: [], revision: 0 })

    void reload()
  }, [reload])

  return { ...state, loading, error, reload }
}
