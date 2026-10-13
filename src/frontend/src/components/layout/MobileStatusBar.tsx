import React, { useEffect, useState } from "react";
import { Mic, Wifi } from "lucide-react";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";

export const MobileStatusBar: React.FC = () => {
  const { isOpen, status, open, close } = useVoiceAssistant();
  const [currentTime, setCurrentTime] = useState(() => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  });

  useEffect(() => {
    const timer = setInterval(() => {
      const d = new Date();
      setCurrentTime(`${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`);
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const isVoiceActive = isOpen && (status === "listening" || status === "processing" || status === "speaking");

  return (
    <div className="relative shrink-0 h-11 px-6 flex items-center justify-between text-xs font-semibold text-slate-900 dark:text-white select-none z-40 bg-transparent">
      {/* Clock */}
      <span className="w-12 text-left font-bold tracking-tight text-[13px]">{currentTime}</span>

      {/* Dynamic Island */}
      <button
        type="button"
        onClick={isOpen ? close : open}
        aria-label={isOpen ? "Thu nhỏ trợ lý giọng nói" : "Mở trợ lý giọng nói"}
        className={`group transition-all duration-300 flex items-center justify-center cursor-pointer ${
          isVoiceActive
            ? "h-7 px-3 bg-black text-white rounded-full ring-2 ring-[#00A699]/60 shadow-lg scale-105"
            : "h-6 w-24 bg-black rounded-full hover:scale-105"
        }`}
      >
        {isVoiceActive ? (
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#00E5C9]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00A699] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00E5C9]" />
            </span>
            <Mic className="w-3.5 h-3.5 text-[#00E5C9]" />
            <span className="text-[10px] tracking-wide">
              {status === "listening" ? "Đang nghe" : status === "processing" ? "Đang xử lý" : "Đang nói"}
            </span>
          </div>
        ) : (
          <div className="flex items-center justify-between w-full px-2">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-900 ring-1 ring-slate-800" />
            <span className="w-2 h-2 rounded-full bg-[#00A699]/80 group-hover:bg-[#00A699] transition-colors" />
          </div>
        )}
      </button>

      {/* Status Icons */}
      <div className="w-16 flex items-center justify-end gap-1.5 text-slate-800 dark:text-slate-200">
        <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
          <rect x="2" y="14" width="3" height="6" rx="0.8" />
          <rect x="7" y="10" width="3" height="10" rx="0.8" />
          <rect x="12" y="6" width="3" height="14" rx="0.8" />
          <rect x="17" y="2" width="3" height="18" rx="0.8" />
        </svg>
        <Wifi className="w-3.5 h-3.5" />
        <div className="flex items-center">
          <div className="w-5 h-2.5 rounded-[4px] border border-current p-[1px] flex items-center">
            <div className="h-full w-full bg-[#00A699] rounded-[2px]" />
          </div>
        </div>
      </div>
    </div>
  );
};
