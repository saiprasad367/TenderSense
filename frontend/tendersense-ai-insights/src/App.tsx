import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import AppLayout from "@/components/AppLayout";
import Dashboard from "./pages/Dashboard";
import UploadScreen from "./pages/Upload";
import Evaluation from "./pages/Evaluation";
import Review from "./pages/Review";
import Audit from "./pages/Audit";
import Reports from "./pages/Reports";
import Login from "./pages/Login";
import Register from "./pages/Register";
import BidderDashboard from "./pages/BidderDashboard";
import BidderApply from "./pages/BidderApply";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) => {
  const { user, role, loading } = useAuth();
  
  if (loading) return <div className="h-screen w-screen flex items-center justify-center">Loading portal...</div>;
  if (!user) return <Navigate to="/login" replace />;
  
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return <Navigate to={role === 'viewer' ? '/bidder' : '/'} replace />;
  }
  
  return <>{children}</>;
};

const AppRoutes = () => {
  const { role } = useAuth();
  
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Main Layout Protected Routes */}
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        {/* Admin/Officer Routes */}
        <Route path="/" element={
          <ProtectedRoute allowedRoles={['admin', 'senior_officer', 'evaluation_officer']}>
            <Dashboard />
          </ProtectedRoute>
        } />
        <Route path="/upload" element={
          <ProtectedRoute allowedRoles={['admin', 'senior_officer', 'evaluation_officer']}>
            <UploadScreen />
          </ProtectedRoute>
        } />
        <Route path="/evaluation" element={
          <ProtectedRoute allowedRoles={['admin', 'senior_officer', 'evaluation_officer']}>
            <Evaluation />
          </ProtectedRoute>
        } />
        <Route path="/review" element={
          <ProtectedRoute allowedRoles={['admin', 'senior_officer', 'evaluation_officer']}>
            <Review />
          </ProtectedRoute>
        } />
        <Route path="/audit" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <Audit />
          </ProtectedRoute>
        } />
        <Route path="/reports" element={
          <ProtectedRoute allowedRoles={['admin', 'senior_officer']}>
            <Reports />
          </ProtectedRoute>
        } />

        {/* Bidder Routes */}
        <Route path="/bidder" element={
          <ProtectedRoute allowedRoles={['viewer']}>
            <BidderDashboard />
          </ProtectedRoute>
        } />
        <Route path="/bidder/apply/:tenderId" element={
          <ProtectedRoute allowedRoles={['viewer']}>
            <BidderApply />
          </ProtectedRoute>
        } />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
