import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import MapExplorer from './pages/MapExplorer'
import Timeline from './pages/Timeline'
import Comparator from './pages/Comparator'
import Reports from './pages/Reports'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/map" element={<MapExplorer />} />
        <Route path="/timeline" element={<Timeline />} />
        <Route path="/compare" element={<Comparator />} />
        <Route path="/reports" element={<Reports />} />
      </Route>
    </Routes>
  )
}
