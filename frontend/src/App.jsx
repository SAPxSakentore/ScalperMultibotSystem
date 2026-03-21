import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Documents from './pages/Documents'
import Agents from './pages/Agents'
import AgentChat from './pages/AgentChat'
import Normatives from './pages/Normatives'
import ShiftReports from './pages/ShiftReports'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="projects/:id/shift-reports" element={<ShiftReports />} />
        <Route path="documents" element={<Documents />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:role/chat" element={<AgentChat />} />
        <Route path="normatives" element={<Normatives />} />
      </Route>
    </Routes>
  )
}
