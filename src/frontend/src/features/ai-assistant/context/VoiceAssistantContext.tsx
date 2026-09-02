import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { notifyBookingCreated } from "@/app/events";
import { getCurrentUser } from "@/features/auth/api";
import { redirectToLoginIfUnauthorized } from "@/features/auth/sessionGuard";
import { clearSessionId, getAccessToken, getSessionId, getUserName, saveAuthSession } from "@/features/auth/storage";
import {
  createRideSession,
  endRideSession,
  getRideSession,
  resetRideConversation,
  sendRideMessage,
  submitSessionFeedback,
} from "@/features/ride/api";
import type { BookingLifecycleStatus, BookingProgress, RideTurn } from "@/features/ride/api";
import type { CompletedBooking } from "@/features/ai-assistant/components/BookingSuccessPanel";
import {
  VoiceAssistantContext,
  type AssistantStatus,
  type Message,
  type VoiceAssistantValue,
} from "./voice-assistant-context";

function buildWelcomeMessage(userName: string): string {
  return `Xin chào ${userName}! Em là trợ lý AloSM, rất vui được đồng hành cùng anh/chị hôm nay 😊 Anh/chị đang cần em hỗ trợ gì ạ — đặt xe, theo dõi chuyến đi, hay có thắc mắc nào khác không?`;
}

export const VoiceAssistantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();

  const [isOpen, setIsOpen] = useState(false);
  const [isConversationOpen, setIsConversationOpen] = useState(false);
  const [status, setStatus] = useState<AssistantStatus>("connecting");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "assistant", text: buildWelcomeMessage(getUserName()) },
  ]);
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [bookingProgress, setBookingProgress] = useState<BookingProgress | null>(null);
  const [lifecycleStatus, setLifecycleStatus] = useState<BookingLifecycleStatus | null>(null);
  const [completedBooking, setCompletedBooking] = useState<CompletedBooking | null>(null);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [isSubmittingRating, setIsSubmittingRating] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [transcriptSessionId, setTranscriptSessionId] = useState<string | null>(null);
  // Chặn gửi trùng khi đang xử lý lượt trước — đọc qua ref để callback luôn thấy
  // trạng thái tức thời mà không phải tạo lại sau mỗi lần render.
  const statusRef = useRef(status);
  statusRef.current = status;

  // A double click, two mounted call surfaces, or a development remount must all
  // share one request. Otherwise two sessions are created and the last request
  // rebinds the token, immediately making the first session stale.
  const newSessionRequestRef = useRef<Promise<boolean> | null>(null);

  const resetConversationUi = useCallback(() => {
    setMessages([{ id: "welcome", role: "assistant", text: buildWelcomeMessage(getUserName()) }]);
    setDraft("");
    setBookingProgress(null);
    setLifecycleStatus(null);
    setCompletedBooking(null);
    setShowConfirmationModal(false);
    setShowSuccessModal(false);
    setSessionEnded(false);
    setNotice(null);
  }, []);

  const applyTurnResult = useCallback((result: RideTurn) => {
    if (result.state?.booking_progress !== undefined) {
      setBookingProgress(result.state.booking_progress ?? null);
    }
    const nextLifecycle = result.state?.booking_lifecycle_status ?? result.booking?.lifecycle_status ?? null;
    if (nextLifecycle) setLifecycleStatus(nextLifecycle);

    if (nextLifecycle === "SUCCESS" && result.booking) {
      setCompletedBooking({
        booking_id: result.booking.booking_id,
        estimated_fare: result.booking.estimated_fare,
        lifecycle_status: "SUCCESS",
      });
      setShowConfirmationModal(false);
      setShowSuccessModal(true);
      return;
    }
    if (nextLifecycle === "FAILED") {
      setCompletedBooking({
        booking_id: result.booking?.booking_id ?? "",
        estimated_fare: result.booking?.estimated_fare ?? 0,
        lifecycle_status: "FAILED",
      });
      setShowConfirmationModal(false);
      setShowSuccessModal(true);
      return;
    }
    // Tín hiệu THẬT (không suy đoán) rằng agent đã thu thập đủ thông tin và đang chờ
    // khách xác nhận — đúng src/agents/workflows/booking_models.py::BookingStep.CONFIRM.
    const readyToConfirm =
      result.state?.current_workflow === "RIDE_BOOKING" && result.state?.current_step === "CONFIRM";
    setShowConfirmationModal(Boolean(readyToConfirm));
  }, []);

  const handleEndOfTurnActions = useCallback(
    (result: RideTurn) => {
      if (result.action === "HANDOFF") setNotice("Yêu cầu đã được chuyển đến tổng đài viên.");
      if (result.action === "END_SESSION") {
        // Agent tự kết thúc hội thoại (vd khách nói "hủy"/"thôi") — chỉ reset PHIÊN
        // HỘI THOẠI, không đăng xuất tài khoản (khác hẳn 2 việc, xem endSession()).
        setSessionId(null);
        localStorage.removeItem("alosm_session_id");
        setSessionEnded(true);
        setShowConfirmationModal(false);
        setNotice("Phiên hội thoại đã kết thúc. Nhấn “Bắt đầu phiên mới” để đặt xe tiếp.");
      }
    },
    [],
  );

  const sendText = useCallback(
    async (value: string): Promise<boolean> => {
      const message = value.trim();
      if (!message || !sessionId || sessionEnded || statusRef.current === "processing") return false;
      setMessages((items) => [...items, { id: `user-${Date.now()}`, role: "user", text: message }]);
      setStatus("processing");
      setNotice(null);
      try {
        const result = await sendRideMessage(sessionId, message, "TEXT");
        setMessages((items) => [...items, { id: result.message_id, role: "assistant", text: result.message }]);
        if (result.booking?.booking_id && result.state?.booking_lifecycle_status === "SUCCESS") {
          notifyBookingCreated(result.booking.booking_id);
        }
        applyTurnResult(result);
        handleEndOfTurnActions(result);
        setStatus("idle");
        return true;
      } catch (error) {
        setStatus("error");
        if (redirectToLoginIfUnauthorized(error, navigate)) return false;
        setNotice(error instanceof Error ? error.message : "Không thể gửi tin nhắn. Vui lòng thử lại.");
        return false;
      }
    },
    [sessionId, sessionEnded, applyTurnResult, handleEndOfTurnActions, navigate],
  );

  // Khởi tạo phiên hội thoại 1 LẦN khi Provider mount (ở AppLayout — ngay sau đăng
  // nhập). Khi có cachedSessionId, chạy song song getCurrentUser + getRideSession
  // để giảm waterfall `connecting` 600-1500ms mà vẫn giữ đúng UX connecting→idle.
  useEffect(() => {
    let cancelled = false;

    const bootstrapSession = async () => {
      setStatus("connecting");
      const cachedSessionId = getSessionId();
      if (cachedSessionId) {
        const [userResult, cachedResult] = await Promise.allSettled([
          getCurrentUser(),
          getRideSession(cachedSessionId),
        ]);
        if (cancelled) return;
        if (cachedResult.status === "fulfilled") {
          setSessionId(cachedSessionId);
          setStatus("idle");
          if (
            userResult.status === "fulfilled" &&
            userResult.value.session_id &&
            userResult.value.session_id !== cachedSessionId
          ) {
            saveAuthSession({
              access_token: getAccessToken() || "",
              user_id: userResult.value.user_id,
              full_name: userResult.value.full_name,
              session_id: userResult.value.session_id,
            });
          }
          return;
        }
        clearSessionId();
        if (userResult.status === "fulfilled") {
          const user = userResult.value;
          if (user.session_id) {
            saveAuthSession({
              access_token: getAccessToken() || "",
              user_id: user.user_id,
              full_name: user.full_name,
              session_id: user.session_id,
            });
            setSessionId(user.session_id);
            setStatus("idle");
            return;
          }
          try {
            const session = await createRideSession();
            if (cancelled) return;
            saveAuthSession({
              access_token: getAccessToken() || "",
              user_id: user.user_id,
              full_name: user.full_name,
              session_id: session.session_id,
            });
            setSessionId(session.session_id);
            setStatus("idle");
            return;
          } catch (error) {
            if (cancelled) return;
            if (redirectToLoginIfUnauthorized(error, navigate)) return;
            setStatus("error");
            setNotice(error instanceof Error ? error.message : "Không thể khởi tạo phiên hội thoại.");
            return;
          }
        }
        if (redirectToLoginIfUnauthorized((userResult as PromiseRejectedResult).reason, navigate)) return;
        setStatus("error");
        setNotice(
          userResult.status === "rejected" && (userResult.reason as Error)?.message
            ? (userResult.reason as Error).message
            : "Không thể khởi tạo phiên hội thoại.",
        );
        return;
      }

      try {
        const user = await getCurrentUser();
        if (cancelled) return;
        if (user.session_id) {
          saveAuthSession({
            access_token: getAccessToken() || "",
            user_id: user.user_id,
            full_name: user.full_name,
            session_id: user.session_id,
          });
          setSessionId(user.session_id);
          setStatus("idle");
          return;
        }
        const session = await createRideSession();
        if (cancelled) return;
        saveAuthSession({
          access_token: getAccessToken() || "",
          user_id: user.user_id,
          full_name: user.full_name,
          session_id: session.session_id,
        });
        setSessionId(session.session_id);
        setStatus("idle");
      } catch (error) {
        if (cancelled) return;
        if (redirectToLoginIfUnauthorized(error, navigate)) return;
        setStatus("error");
        setNotice(error instanceof Error ? error.message : "Không thể khởi tạo phiên hội thoại.");
      }
    };

    bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => {
    setIsConversationOpen(false);
    setIsOpen(false);
  }, []);
  const openConversation = useCallback(() => setIsConversationOpen(true), []);
  const closeConversation = useCallback(() => setIsConversationOpen(false), []);

  const openWithPrefill = useCallback((prefill: string) => {
    setDraft(prefill);
    setIsConversationOpen(true);
    setIsOpen(true);
  }, []);

  const confirmBooking = useCallback(async () => {
    // Gửi đúng 1 lượt hội thoại thật ("Xác nhận đặt xe" khớp _CONFIRM_TERMS ở
    // src/agents/understanding/rules.py) — KHÔNG có endpoint tạo booking riêng ở
    // frontend. Đặt xe luôn đi qua agent thật, không bao giờ tạo trực tiếp từ UI.
    await sendText("Xác nhận đặt xe");
  }, [sendText]);

  const dismissConfirmation = useCallback(() => setShowConfirmationModal(false), []);
  const closeSuccessModal = useCallback(() => setShowSuccessModal(false), []);

  const submitRating = useCallback(
    async (rating: number, comment?: string): Promise<boolean> => {
      if (!sessionId) return false;
      setIsSubmittingRating(true);
      try {
        await submitSessionFeedback(sessionId, rating, comment?.trim() || undefined);
        return true;
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "Không thể gửi đánh giá.");
        return false;
      } finally {
        setIsSubmittingRating(false);
      }
    },
    [sessionId],
  );

  const endSession = useCallback(async () => {
    if (sessionId) {
      await endRideSession(sessionId).catch(() => undefined);
    }
    setSessionId(null);
    clearSessionId();
    setSessionEnded(true);
    setShowConfirmationModal(false);
    setShowSuccessModal(false);
    setNotice("Phiên hội thoại đã kết thúc. Nhấn “Bắt đầu phiên mới” để đặt xe tiếp.");
  }, [sessionId]);

  const newSession = useCallback((): Promise<boolean> => {
    if (newSessionRequestRef.current) return newSessionRequestRef.current;

    let request: Promise<boolean>;
    request = (async () => {
      // `agent_state` (bao gồm conversation_history) chỉ thuộc về một session ở
      // backend. Kết thúc session hiện tại rồi tạo ID mới là reset memory thật, không
      // chỉ là xóa bubble ở UI. Hỏi auth source-of-truth trước để không gửi `/end`
      // cho session cache cũ đã bị tab/cuộc gọi khác rebind.
      try {
        setStatus("connecting");
        const user = await getCurrentUser();
        if (sessionId && user.session_id === sessionId) {
          await endRideSession(sessionId).catch(() => undefined);
        }
        const session = await createRideSession();
        saveAuthSession({
          access_token: getAccessToken() || "",
          user_id: user.user_id,
          full_name: user.full_name,
          session_id: session.session_id,
        });
        setSessionId(session.session_id);
        setStatus("idle");
        resetConversationUi();
        return true;
      } catch (error) {
        if (redirectToLoginIfUnauthorized(error, navigate)) return false;
        setSessionId(null);
        setSessionEnded(true);
        setShowConfirmationModal(false);
        setShowSuccessModal(false);
        setStatus("error");
        setNotice(error instanceof Error ? error.message : "Không thể tạo phiên mới.");
        clearSessionId();
        return false;
      }
    })().finally(() => {
      if (newSessionRequestRef.current === request) newSessionRequestRef.current = null;
    });

    newSessionRequestRef.current = request;
    return request;
  }, [sessionId, navigate, resetConversationUi]);

  const resetConversation = useCallback(async () => {
    if (!sessionId || sessionEnded || statusRef.current === "processing") return;
    try {
      setStatus("processing");
      await resetRideConversation(sessionId);
      resetConversationUi();
      setStatus("idle");
    } catch (error) {
      if (redirectToLoginIfUnauthorized(error, navigate)) return;
      setStatus("error");
      setNotice(error instanceof Error ? error.message : "Không thể đặt lại cuộc hội thoại.");
    }
  }, [sessionId, sessionEnded, navigate, resetConversationUi]);

  const openHistory = useCallback(() => setIsHistoryOpen(true), []);
  const closeHistory = useCallback(() => setIsHistoryOpen(false), []);
  const openTranscript = useCallback((id: string) => setTranscriptSessionId(id), []);
  const closeTranscript = useCallback(() => setTranscriptSessionId(null), []);
  const value = useMemo<VoiceAssistantValue>(
    () => ({
      isOpen,
      open,
      close,
      isConversationOpen,
      openConversation,
      closeConversation,
      openWithPrefill,
      draft,
      setDraft,
      status,
      messages,
      notice,
      sessionId,
      sessionEnded,
      sendText,
      endSession,
      newSession,
      resetConversation,
      bookingProgress,
      lifecycleStatus,
      showConfirmationModal,
      confirmBooking,
      dismissConfirmation,
      showSuccessModal,
      completedBooking,
      closeSuccessModal,
      submitRating,
      isSubmittingRating,
      isHistoryOpen,
      openHistory,
      closeHistory,
      transcriptSessionId,
      openTranscript,
      closeTranscript,
    }),
    [
      isOpen,
      open,
      close,
      isConversationOpen,
      openConversation,
      closeConversation,
      openWithPrefill,
      draft,
      setDraft,
      status,
      messages,
      notice,
      sessionId,
      sessionEnded,
      sendText,
      endSession,
      newSession,
      resetConversation,
      bookingProgress,
      lifecycleStatus,
      showConfirmationModal,
      confirmBooking,
      dismissConfirmation,
      showSuccessModal,
      completedBooking,
      closeSuccessModal,
      submitRating,
      isSubmittingRating,
      isHistoryOpen,
      openHistory,
      closeHistory,
      transcriptSessionId,
      openTranscript,
      closeTranscript,
    ],
  );

  return <VoiceAssistantContext.Provider value={value}>{children}</VoiceAssistantContext.Provider>;
};
