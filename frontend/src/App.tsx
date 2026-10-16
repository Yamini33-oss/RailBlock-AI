import { Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import PlaceholderPage from './pages/PlaceholderPage'
import MaintenanceRequestPage from './pages/MaintenanceRequestPage'
import ScheduleTrafficPage from './pages/ScheduleTrafficPage'
import BlockPlanningPage from './pages/BlockPlanningPage'
import ConflictCenterPage from './pages/ConflictCenterPage'
import WindowComparisonPage from './pages/WindowComparisonPage'
import WhatIfPage from './pages/WhatIfPage'
import DecisionHistoryPage from './pages/DecisionHistoryPage'
import ModuleStatusPage from './pages/ModuleStatusPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />

        <Route
          path="request"
          element={<MaintenanceRequestPage />}
        />

        <Route
          path="schedule"
          element={<ScheduleTrafficPage />}
        />

        <Route
          path="recommendation"
          element={<BlockPlanningPage />}
        />

        <Route
          path="conflicts"
          element={<ConflictCenterPage />}
        />

        <Route
          path="compare"
          element={<WindowComparisonPage />}
        />

        <Route
          path="whatif"
          element={<WhatIfPage />}
        />

        <Route
          path="history"
          element={<DecisionHistoryPage />}
        />

        <Route
          path="modules"
          element={<ModuleStatusPage />}
        />
      </Route>
    </Routes>
  )
}