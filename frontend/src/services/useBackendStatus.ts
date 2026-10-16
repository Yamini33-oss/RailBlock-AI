import { useEffect, useState } from 'react'
import type { ModuleStatus } from '../types'
import { checkBackendHealth } from './api'

export function useBackendStatus(intervalMs = 15000): ModuleStatus {
  const [status, setStatus] = useState<ModuleStatus>('NOT CONNECTED')

  useEffect(() => {
    let active = true
    const run = async () => {
      const s = await checkBackendHealth()
      if (active) setStatus(s)
    }
    run()
    const id = setInterval(run, intervalMs)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [intervalMs])

  return status
}
