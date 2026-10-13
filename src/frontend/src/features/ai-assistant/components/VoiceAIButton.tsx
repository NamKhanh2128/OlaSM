import React from "react";
import { Mic } from "lucide-react";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";

export const VoiceAIButton: React.FC = () => {
  const { isOpen, open, status } = useVoiceAssistant();

  if (isOpen) return null;

  return (
    <button
      type="button"
      onClick={open}
      aria-label="Gọi Trợ lý giọng nói Green SM"
      aria-expanded={isOpen}
      className={`absolute z-30 bottom-20 right-4 flex items-center gap-2 pl-3.5 pr-4 py-2.5 rounded-full shadow-[0_8px_25px_rgba(0,166,153,0.35)] transition-all duration-300 cursor-pointer
        bg-gradient-to-r from-[#00A699] to-[#00C9B7] text-white hover:scale-105 active:scale-95 border border-white/30
        ${status === "listening" ? "ring-4 ring-[#00E5C9]/40 animate-pulse" : ""}`}
    >
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-80" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-white" />
      </span>
      <Mic className="w-4 h-4 text-white" />
      <span className="text-xs font-bold tracking-tight">Nói với Trợ lý</span>
    </button>
  );
};
