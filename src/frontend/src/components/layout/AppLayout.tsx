import React, { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { MobileNav } from "./MobileNav";
import { MobileStatusBar } from "./MobileStatusBar";
import { MobileAppHeader } from "./MobileAppHeader";
import { VoiceAssistantProvider } from "@/features/ai-assistant/context/VoiceAssistantContext";
import { VoiceAIButton } from "@/features/ai-assistant/components/VoiceAIButton";
import { VoiceAssistantPopup } from "@/features/ai-assistant/components/VoiceAssistantPopup";
import { getUserRole } from "@/features/auth/storage";
import { Smartphone, MonitorSmartphone, Sparkles, ShieldCheck, Zap } from "lucide-react";
import logoSvg from "@/assets/logo.svg";

const AppShell: React.FC<{ isOperator: boolean }> = ({ isOperator }) => {
  const [isPhoneMockup, setIsPhoneMockup] = useState(true);

  return (
    <div className="min-h-screen w-full bg-[#071318] dark:bg-[#050D11] text-slate-100 flex flex-col items-center justify-center p-0 md:p-6 transition-colors duration-200 selection:bg-[#00A699]/30">
      {/* Desktop Presentation Header (Ẩn trên mobile thật) */}
      <div className="hidden md:flex w-full max-w-4xl items-center justify-between mb-4 px-2">
        <div className="flex items-center gap-3">
          <img src={logoSvg} alt="Green SM Logo" className="h-9 w-auto brightness-110" />
          <div className="border-l border-white/20 pl-3">
            <h1 className="text-sm font-extrabold tracking-wide text-white flex items-center gap-2">
              Green SM Mobile Simulator
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#00A699]/20 text-[#00E5C9] border border-[#00A699]/30">
                OlaSM Voice Core v2.0
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Trợ lý giọng nói thông minh nhúng trong app mobile Green SM (VinGroup)
            </p>
          </div>
        </div>

        {/* Viewport Mode Switcher */}
        <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-2xl p-1 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setIsPhoneMockup(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
              isPhoneMockup
                ? "bg-[#00A699] text-white shadow-md shadow-[#00A699]/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>Khung điện thoại</span>
          </button>
          <button
            type="button"
            onClick={() => setIsPhoneMockup(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
              !isPhoneMockup
                ? "bg-[#00A699] text-white shadow-md shadow-[#00A699]/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <MonitorSmartphone className="w-3.5 h-3.5" />
            <span>Toàn màn hình</span>
          </button>
        </div>
      </div>

      {/* Main Mobile App Frame */}
      <div
        className={`relative flex flex-col overflow-hidden transition-all duration-300 ${
          isPhoneMockup
            ? "w-full max-w-[412px] h-[100dvh] md:h-[870px] md:max-h-[92vh] md:rounded-[50px] md:border-[10px] md:border-slate-900 phone-chassis bg-[#F4FBFA] dark:bg-[#0B1317] text-[#191C1E] dark:text-slate-100"
            : "w-full max-w-lg min-h-screen bg-[#F4FBFA] dark:bg-[#0B1317] text-[#191C1E] dark:text-slate-100 shadow-2xl"
        }`}
      >
        {/* iOS Dynamic Island & Status Bar */}
        <MobileStatusBar />

        {/* Green SM Mobile Header */}
        <MobileAppHeader />

        {/* Scrollable Screen Content */}
        <main className="flex-1 min-h-0 overflow-y-auto no-scrollbar relative p-4 pb-20">
          <Outlet />

          {/* Voice Assistant Button (FAB) inside phone screen */}
          {!isOperator ? <VoiceAIButton /> : null}

          {/* Voice Assistant Mobile Bottom Sheet inside phone screen */}
          {!isOperator ? <VoiceAssistantPopup /> : null}
        </main>

        {/* Mobile Bottom Tab Navigation */}
        <MobileNav />

        {/* iOS Home Indicator Bar */}
        <div className="shrink-0 h-4 flex items-center justify-center bg-white dark:bg-[#12191F]">
          <div className="w-32 h-1 bg-slate-300 dark:bg-slate-700 rounded-full" />
        </div>
      </div>

      {/* Ambient Features Footer (Desktop Presentation) */}
      <div className="hidden md:flex items-center gap-6 mt-4 text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-[#00A699]" />
          VinGroup Guardrails: Rủi ro tài chính & xác thực sinh trắc học
        </span>
        <span className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          LiveKit WebRTC Audio Realtime (Độ trễ &lt; 300ms)
        </span>
        <span className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-[#00E5C9]" />
          Typed AppAction Topic: olasm.app_control.v1
        </span>
      </div>
    </div>
  );
};

export const AppLayout: React.FC = () => {
  const isOperator = getUserRole() === "OPERATOR" || getUserRole() === "ADMIN";
  const location = useLocation();

  if (isOperator && location.pathname !== "/operator") {
    return <Navigate to="/operator" replace />;
  }

  if (isOperator) {
    return <AppShell isOperator />;
  }

  return (
    <VoiceAssistantProvider>
      <AppShell isOperator={false} />
    </VoiceAssistantProvider>
  );
};
