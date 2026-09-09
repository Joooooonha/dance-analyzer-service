import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthProvider';
import { useAuth } from './auth/useAuth';
import Header from './components/Header';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Practice from './pages/Practice';
import Assignments from './pages/Assignments';
import AssignmentDetail from './pages/AssignmentDetail';
import AssignmentCreate from './pages/AssignmentCreate';
import Logs from './pages/Logs';
import LogDetail from './pages/LogDetail';
import './App.css';

// 로그인 여부를 확인하는 동안 보여줄 화면.
// 이게 없으면 확인이 끝나기 전에 판단해버려서, 로그인한 사용자가 로그인
// 화면으로 튕겨나갔다가 되돌아오는 깜빡임이 생긴다.
function AuthGate() {
  return (
    <div className="loading">
      <div className="spinner"></div>
    </div>
  );
}

// 로그인 필요 라우트 보호
function ProtectedRoute({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <AuthGate />;
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// 이미 로그인한 사용자는 대시보드로 리다이렉트
function PublicRoute({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <AuthGate />;
  if (user) {
    return <Navigate to="/" replace />;
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <div className="app">
        <Header />
        <main className="main-content">
          <Routes>
            {/* 공개 라우트 */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />
            <Route
              path="/signup"
              element={
                <PublicRoute>
                  <Signup />
                </PublicRoute>
              }
            />

            {/* 보호된 라우트 */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/practice"
              element={
                <ProtectedRoute>
                  <Practice />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assignments"
              element={
                <ProtectedRoute>
                  <Assignments />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assignments/new"
              element={
                <ProtectedRoute>
                  <AssignmentCreate />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assignments/:id"
              element={
                <ProtectedRoute>
                  <AssignmentDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/logs"
              element={
                <ProtectedRoute>
                  <Logs />
                </ProtectedRoute>
              }
            />
            <Route
              path="/logs/:id"
              element={
                <ProtectedRoute>
                  <LogDetail />
                </ProtectedRoute>
              }
            />

            {/* 404 리다이렉트 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
