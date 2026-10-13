import React from "react";
import { Bell, ChevronDown, MapPin, Sparkles, User } from "lucide-react";
import { Link } from "react-router-dom";
import { getUserName } from "@/features/auth/storage";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";

export const MobileAppHeader: React.FC = () => {
  const userName = getUserName();
  const { open } = useVoiceAssistant();

  return (
    <header className="shrink-0 px-4 pt-2 pb-3 bg-white/90 dark:bg-[#12191F]/90 backdrop-blur-md border-b border-slate-100 dark:border-white/5 flex items-center justify-between z-20">
      {/* Left: User Avatar & Location Pin */}
      <div className="flex items-center gap-2.5 min-w-0">
        <Link
          to="/profile"
          className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-tr from-[#00A699] to-[#00C9B7] text-white shadow-sm ring-2 ring-white dark:ring-slate-800"
          aria-label="Tài khoản cá nhân"
        >
          <User className="w-4 h-4" />
          <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-400 border-2 border-white dark:border-slate-900 rounded-full" />
        </Link>
        <div className="min-w-0">
          <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            <span>Chào {userName || "bạn"}</span>
            <ChevronDown className="w-3 h-3" />
          </div>
          <div className="flex items-center gap-1 text-xs font-bold text-slate-800 dark:text-slate-100 truncate">
            <MapPin className="w-3.5 h-3.5 text-[#00A699] shrink-0" />
            <span className="truncate">72 Lê Thánh Tôn, Bến Nghé, Q.1</span>
          </div>
        </div>
      </div>

      {/* Right: Quick Voice Trigger & Notification */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={open}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-[#E7FBF9] text-[#00A699] dark:bg-[#00A699]/15 dark:text-[#00E5C9] text-xs font-bold transition hover:scale-105 active:scale-95 cursor-pointer"
          title="Gọi trợ lý giọng nói Green SM"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="text-[11px]">Trợ lý</span>
        </button>

        <Link
          to="/activity"
          className="relative grid h-8 w-8 place-items-center rounded-full bg-slate-100 text-slate-600 hover:text-slate-900 dark:bg-white/10 dark:text-slate-300 transition"
          aria-label="Thông báo và hoạt động"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#00A699]" />
        </Link>
      </div>
    </header>
  );
};
