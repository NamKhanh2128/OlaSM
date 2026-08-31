import React, { Suspense, lazy, useEffect } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { RequireRole } from "@/features/auth/RequireRole";
import { AppLayout } from "@/components/layout/AppLayout";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";
import { LoginPage } from "@/pages/Login/LoginPage";
import { HomePage } from "@/pages/Home/HomePage";
import { NotFoundPage } from "@/pages/NotFound/NotFoundPage";
import { PoliciesPage } from "@/pages/Policies/PoliciesPage";
import { CookieConsentBanner } from "@/features/policies/CookieConsentBanner";

const BookingPage = lazy(() => import("@/pages/Booking/BookingPage").then((m) => ({ default: m.BookingPage })));
const TrackingPage = lazy(() => import("@/pages/Tracking/TrackingPage").then((m) => ({ default: m.TrackingPage })));
const ActivityPage = lazy(() => import("@/pages/Activity/ActivityPage").then((m) => ({ default: m.ActivityPage })));
const PaymentPage = lazy(() => import("@/pages/Payment/PaymentPage").then((m) => ({ default: m.PaymentPage })));
const ProfilePage = lazy(() => import("@/pages/Profile/ProfilePage").then((m) => ({ default: m.ProfilePage })));
const OperatorPage = lazy(() => import("@/pages/Operator/OperatorPage").then((m) => ({ default: m.OperatorPage })));

const RouteFallback: React.FC = () => (
  <div className="mx-auto max-w-6xl p-8 text-sm text-slate-400">Đang tải…</div>
);

// Voice AI không còn là trang riêng "/assistant" — giờ là nút nổi + popup khả dụng ở
// mọi trang (xem AppLayout.tsx). Route này chỉ còn để không phá các đường dẫn cũ đã
// lưu/đánh dấu (bookmark) hay bất kỳ chỗ nào lỡ còn trỏ tới "/assistant": mở popup
// thay vì hiện trang 404, rồi quay về Trang chủ.
const AssistantRedirect: React.FC = () => {
  const { open } = useVoiceAssistant();
  useEffect(() => {
    open();
  }, [open]);
  return <Navigate to="/" replace />;
};

// `/login` đứng riêng (chưa đăng nhập, chưa có gì để điều hướng tới). Mọi trang sau
// đăng nhập giờ lồng trong AppLayout (Sidebar/Topbar/MobileNav + VoiceAssistantProvider)
// để LUÔN có thanh điều hướng sang màn khác và Voice AI khả dụng xuyên suốt.
const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/policies",
    element: <PoliciesPage />,
  },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/booking", element: <Suspense fallback={<RouteFallback />}><BookingPage /></Suspense> },
      { path: "/tracking", element: <Suspense fallback={<RouteFallback />}><TrackingPage /></Suspense> },
      { path: "/activity", element: <Suspense fallback={<RouteFallback />}><ActivityPage /></Suspense> },
      { path: "/payment", element: <Suspense fallback={<RouteFallback />}><PaymentPage /></Suspense> },
      { path: "/profile", element: <Suspense fallback={<RouteFallback />}><ProfilePage /></Suspense> },
      {
        path: "/operator",
        element: (
          <RequireRole roles={["OPERATOR", "ADMIN"]}>
            <Suspense fallback={<RouteFallback />}><OperatorPage /></Suspense>
          </RequireRole>
        ),
      },
      { path: "/assistant", element: <AssistantRedirect /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

export const AppRouter: React.FC = () => (
  <>
    <RouterProvider router={router} />
    <CookieConsentBanner />
  </>
);
