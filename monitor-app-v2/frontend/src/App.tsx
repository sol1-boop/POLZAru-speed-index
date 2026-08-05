import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DomainsPage from './pages/DomainsPage'
import DomainDetailPage from './pages/DomainDetailPage'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
      
      <Route path="/" element={isAuthenticated ? <Layout /> : <Navigate to="/login" />}>
        <Route index element={<DashboardPage />} />
        <Route path="domains" element={<DomainsPage />} />
        <Route path="domains/:id" element={<DomainDetailPage />} />
      </Route>
    </Routes>
  )
}

export default App
