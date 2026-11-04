import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import { queryKeys } from './api/queryKeys'
import type { CurrentUser } from './types'
import { normalizeUser } from './api/normalize'
import AppShell from './components/AppShell'
import AdminShell from './components/AdminShell'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import HomePage from './pages/HomePage'
import ProductsPage from './pages/ProductsPage'
import ProductDetailPage from './pages/ProductDetailPage'
import CartPage from './pages/CartPage'
import CheckoutPage from './pages/CheckoutPage'
import OrdersPage from './pages/OrdersPage'
import OrderDetailPage from './pages/OrderDetailPage'
import MessagesPage from './pages/MessagesPage'
import ProfilePage from './pages/ProfilePage'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminProductsPage from './pages/admin/AdminProductsPage'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AdminMessagesPage from './pages/admin/AdminMessagesPage'
import AdminSettingsPage from './pages/admin/AdminSettingsPage'
import NotFoundPage from './pages/NotFoundPage'

export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: async () => {
      const session = await api.get<{ type: string; user?: unknown; admin?: unknown }>('/auth/me')
      return normalizeUser(session.type === 'admin' ? session.admin : session.user) as CurrentUser
    },
    retry: false,
  })
}

function ProtectedRoute({ role }: { role?: 'MEMBER' | 'ADMIN' }) {
  const location = useLocation()
  const { data: user, isLoading } = useCurrentUser()
  if (isLoading) return <div className="route-loading"><Spin size="large" /></div>
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (role === 'MEMBER' && user.role !== 'MEMBER') return <Navigate to="/admin" replace />
  if (role === 'ADMIN' && user.role === 'MEMBER') return <Navigate to="/member/home" replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute role="MEMBER" />}>
        <Route element={<AppShell />}>
          <Route path="/member/home" element={<HomePage />} />
          <Route path="/member/products" element={<ProductsPage />} />
          <Route path="/member/products/:id" element={<ProductDetailPage />} />
          <Route path="/member/cart" element={<CartPage />} />
          <Route path="/member/checkout" element={<CheckoutPage />} />
          <Route path="/member/orders" element={<OrdersPage />} />
          <Route path="/member/orders/:id" element={<OrderDetailPage />} />
          <Route path="/member/messages" element={<MessagesPage />} />
          <Route path="/member/profile" element={<ProfilePage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute role="ADMIN" />}>
        <Route element={<AdminShell />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/products" element={<AdminProductsPage />} />
          <Route path="/admin/orders" element={<AdminOrdersPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/messages" element={<AdminMessagesPage />} />
          <Route path="/admin/settings" element={<AdminSettingsPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/member/home" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
