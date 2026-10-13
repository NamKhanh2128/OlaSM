import React from "react";
import { History, RotateCcw, X, Sparkles } from "lucide-react";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";
import { VoiceCallPanel } from "@/features/ai-assistant/components/VoiceCallPanel";
import { BookingConfirmationModal } from "@/features/ai-assistant/components/BookingConfirmationModal";
import { BookingSuccessModal } from "@/features/ai-assistant/components/BookingSuccessModal";
import { HistoryPanel } from "@/features/history/components/HistoryPanel";
import { TranscriptModal } from "@/features/history/components/TranscriptModal";

export const VoiceAssistantPopup: React.FC = () => {
  const {
    isOpen,
    close,
    resetConversation,
    isHistoryOpen,
    openHistory,
    closeHistory,
    transcriptSessionId,
    openTranscript,
    closeTranscript,
  } = useVoiceAssistant();

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Trợ lý giọng nói Green SM"
      className="absolute inset-0 z-50 bg-black/50 backdrop-blur-sm flex flex-col justify-end animate-in fade-in duration-200"
    >
      <div
        className="relative w-full h-[90%] max-h-[90%] bg-white dark:bg-[#10171D]
          rounded-t-[32px] shadow-2xl flex flex-col overflow-hidden
          border-t border-slate-200/80 dark:border-white/10
          animate-in slide-in-from-bottom-6 duration-300"
      >
        {/* Drag Handle Bar */}
        <div className="pt-2.5 pb-1 flex justify-center shrink-0">
          <div className="w-12 h-1 bg-slate-300 dark:bg-slate-700 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 dark:border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-[#E7FBF9] text-[#00A699] dark:bg-[#00A699]/20 dark:text-[#00E5C9]">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs font-extrabold text-slate-900 dark:text-white leading-tight">
                Trợ lý giọng nói Green SM
              </p>
              <p className="text-[10px] text-slate-400 font-medium">OlaSM Voice Core</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => void resetConversation()}
              aria-label="Tạo lại hội thoại"
              title="Tạo lại hội thoại"
              className="text-slate-400 hover:text-[#00A699] p-1.5 rounded-full hover:bg-[#00A699]/10 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={openHistory}
              aria-label="Lịch sử hội thoại"
              title="Lịch sử hội thoại"
              className="text-slate-400 hover:text-slate-900 dark:hover:text-white p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
            >
              <History className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={close}
              aria-label="Đóng trợ lý"
              className="text-slate-400 hover:text-slate-900 dark:hover:text-white p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Call Panel / Modals */}
        <div className="relative flex-1 min-h-0 overflow-hidden">
          <VoiceCallPanel />
          <BookingConfirmationModal />
          <BookingSuccessModal />
        </div>

        <HistoryPanel isOpen={isHistoryOpen} onClose={closeHistory} onSelectSession={openTranscript} />
        <TranscriptModal sessionId={transcriptSessionId} onClose={closeTranscript} />
      </div>
    </div>
  );
};
