import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "../store/auth";
import { AppLayout } from "../layouts/AppLayout";
import { LoginPage } from "../pages/LoginPage";

const DashboardPage = lazy(() => import("../pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const TenantsPage = lazy(() => import("../pages/TenantsPage").then((module) => ({ default: module.TenantsPage })));
const MembersPage = lazy(() => import("../pages/MembersPage").then((module) => ({ default: module.MembersPage })));
const OpsPage = lazy(() => import("../pages/OpsPage").then((module) => ({ default: module.OpsPage })));
const AnalyticsPage = lazy(() => import("../pages/AnalyticsPage").then((module) => ({ default: module.AnalyticsPage })));
const SystemPage = lazy(() => import("../pages/SystemPage").then((module) => ({ default: module.SystemPage })));
const AuditLogsPage = lazy(() => import("../pages/AuditLogsPage").then((module) => ({ default: module.AuditLogsPage })));
const AIReplyPage = lazy(() => import("../pages/AIReplyPage").then((module) => ({ default: module.AIReplyPage })));
const SettingsPage = lazy(() => import("../pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));

function RouteSuspense({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="fullscreen-center">
          <Spin size="large" />
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function ProtectedRoutes() {
  return (
    <AppLayout>
      <RouteSuspense>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/tenants" element={<TenantsPage />} />
          <Route path="/accounts" element={<Navigate to="/ops?tab=accounts&platform=all" replace />} />
          <Route path="/members" element={<MembersPage />} />
          <Route path="/targets" element={<Navigate to="/ops?tab=targets&platform=all" replace />} />
          <Route path="/comments" element={<Navigate to="/ops?tab=inbox&platform=all" replace />} />
          <Route path="/replies" element={<Navigate to="/ops?tab=replies&platform=all" replace />} />
          <Route path="/douyin" element={<Navigate to="/ops?tab=accounts&platform=douyin" replace />} />
          <Route path="/ops" element={<OpsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/audit" element={<AuditLogsPage />} />
          <Route path="/ai-reply" element={<AIReplyPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </RouteSuspense>
    </AppLayout>
  );
}

export function AppRouter() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="fullscreen-center">
        <Spin size="large" />
      </div>
    );
  }

  if (!token) {
    return <LoginPage />;
  }

  return <ProtectedRoutes />;
}
