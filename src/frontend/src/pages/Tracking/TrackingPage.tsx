import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { TrackingTripDetails } from "@/features/tracking/types";
import { getTripStatus, TRIP_STATUS_TEXT, type TripStatusResponse } from "@/features/tracking/api";
import { redirectToLoginIfUnauthorized } from "@/features/auth/sessionGuard";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";
import {
  Navigation,
  AlertCircle,
  Sparkles,
  Car,
  Phone,
  MessageSquare,
  ShieldCheck,
  ChevronLeft,
} from "lucide-react";

const POLL_INTERVAL_MS = 4000;

const STATUS_MAP: Record<TripStatusResponse["status"], TrackingTripDetails["status"]> = {
  SEARCHING_DRIVER: "searching",
  DRIVER_ASSIGNED: "accepted",
  ARRIVING: "arriving",
  ON_TRIP: "in_transit",
  COMPLETED: "completed",
};

const PICKUP_POINT = { left: 28, top: 58 };
const DESTINATION_POINT = { left: 74, top: 24 };
const DRIVER_WAYPOINT: Record<TrackingTripDetails["status"], { left: number; top: number } | null> = {
  searching: null,
  accepted: { left: 82, top: 78 },
  arriving: { left: 42, top: 62 },
  in_transit: { left: 52, top: 38 },
  completed: DESTINATION_POINT,
};

export const TrackingPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { open: openAssistant } = useVoiceAssistant();
  const routeState = location.state as
    | { sessionId?: string; bookingId?: string; pickup?: string; destination?: string }
    | undefined;

  const [trip, setTrip] = useState<TrackingTripDetails | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!routeState?.sessionId || !routeState?.bookingId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const status = await getTripStatus(routeState.sessionId!);
        if (cancelled) return;
        setTrip({
          bookingId: routeState.bookingId!,
          status: STATUS_MAP[status.status],
          statusText: TRIP_STATUS_TEXT[status.status],
          pickup: routeState.pickup || "Điểm đón",
          destination: routeState.destination || "Điểm đến",
          eta: status.eta_minutes != null ? `${status.eta_minutes} phút` : "--",
          driver:
            status.driver_name != null
              ? {
                  name: status.driver_name,
                  avatar:
                    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                  vehicleName: status.vehicle || "VinFast VF e34",
                  licensePlate: status.license_plate || "51K-889.32",
                  rating: status.driver_rating ?? 5.0,
                  phone: status.driver_phone || "0901234567",
                }
              : undefined,
        });
      } catch (error) {
        if (cancelled) return;
        if (redirectToLoginIfUnauthorized(error, navigate)) return;
        setNotice(error instanceof Error ? error.message : "Không thể tải trạng thái chuyến đi.");
      }
    };

    poll();
    const interval = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [routeState?.sessionId, routeState?.bookingId, routeState?.pickup, routeState?.destination, navigate]);

  // Demo fallback trip if navigated without state for testing/demo
  const activeTrip: TrackingTripDetails = trip || {
    bookingId: "GSM-DEMO-889",
    status: "arriving",
    statusText: "Tài xế đang đến điểm đón",
    pickup: "72 Lê Thánh Tôn, Bến Nghé, Quận 1",
    destination: "Vincom Landmark 81, P.22, Bình Thạnh",
    eta: "3 phút",
    driver: {
      name: "Trần Minh Trí",
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
      vehicleName: "VinFast VF 8 (Xanh SM Luxury)",
      licensePlate: "51K-999.88",
      rating: 5.0,
      phone: "0909123456",
    },
  };

  const driverPos = DRIVER_WAYPOINT[activeTrip.status] || { left: 45, top: 62 };

  return (
    <div className="space-y-3 pb-4">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-slate-800 dark:hover:text-white cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Quay lại</span>
        </button>
        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#E7FBF9] text-[#00A699] dark:bg-[#00A699]/15 dark:text-[#00E5C9] flex items-center gap-1">
          <Navigation className="w-3 h-3 animate-spin" />
          GPS Trực tiếp
        </span>
      </div>

      {notice && (
        <div className="p-2.5 rounded-xl bg-amber-50 text-amber-800 text-xs flex items-center gap-2 dark:bg-amber-500/10 dark:text-amber-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {/* Simulated High-Res Mobile Map Screen */}
      <div className="h-60 w-full rounded-2xl overflow-hidden relative border border-slate-200/80 dark:border-white/10 bg-[#0f172a] shadow-inner select-none">
        {/* Map Grid Pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:16px_16px] opacity-70" />

        {/* Simulated Route Vector Line */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M 110 140 Q 170 120 210 90 T 290 56"
            fill="none"
            stroke="#00A699"
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray="8 6"
            className="animate-pulse"
          />
        </svg>

        {/* Pickup Pin */}
        <div
          className="absolute transform -translate-x-1/2 -translate-y-full flex flex-col items-center"
          style={{ left: `${PICKUP_POINT.left}%`, top: `${PICKUP_POINT.top}%` }}
        >
          <span className="grid h-6 w-6 place-items-center rounded-full bg-[#00A699] text-white shadow-md ring-2 ring-white text-[10px] font-bold">
             đón
          </span>
          <span className="text-[9px] font-bold bg-white dark:bg-slate-900 text-slate-800 dark:text-white px-1.5 py-0.5 rounded shadow mt-0.5 whitespace-nowrap">
            72 Lê Thánh Tôn
          </span>
        </div>

        {/* Destination Pin */}
        <div
          className="absolute transform -translate-x-1/2 -translate-y-full flex flex-col items-center"
          style={{ left: `${DESTINATION_POINT.left}%`, top: `${DESTINATION_POINT.top}%` }}
        >
          <span className="grid h-6 w-6 place-items-center rounded-full bg-rose-600 text-white shadow-md ring-2 ring-white text-[10px] font-bold">
            đến
          </span>
          <span className="text-[9px] font-bold bg-white dark:bg-slate-900 text-slate-800 dark:text-white px-1.5 py-0.5 rounded shadow mt-0.5 whitespace-nowrap">
            Landmark 81
          </span>
        </div>

        {/* Live Moving Electric Vehicle Marker */}
        <div
          className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center transition-all duration-1000 ease-in-out z-20"
          style={{ left: `${driverPos.left}%`, top: `${driverPos.top}%` }}
        >
          <div className="relative">
            <span className="absolute -inset-1.5 rounded-full bg-[#00A699]/40 animate-ping" />
            <div className="relative grid h-9 w-9 place-items-center rounded-full bg-gradient-to-tr from-[#00A699] to-[#00C9B7] text-white shadow-xl ring-2 ring-white">
              <Car className="w-5 h-5" />
            </div>
          </div>
          <span className="mt-1 px-1.5 py-0.5 rounded-full bg-black/80 text-white text-[9px] font-extrabold backdrop-blur">
            {activeTrip.eta}
          </span>
        </div>
      </div>

      {/* Driver Card & Trip Info (Green SM Mobile Style) */}
      <div className="rounded-2xl p-3.5 bg-white dark:bg-[#152026] border border-slate-200/80 dark:border-white/10 shadow-sm space-y-3">
        {/* Status Header */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-white/5">
          <div>
            <p className="text-xs font-extrabold text-[#00A699] dark:text-[#00E5C9]">
              {activeTrip.statusText}
            </p>
            <p className="text-[10px] text-slate-400">Mã chuyến: {activeTrip.bookingId}</p>
          </div>
          <div className="text-right">
            <span className="text-sm font-extrabold text-slate-900 dark:text-white">
              {activeTrip.eta}
            </span>
            <p className="text-[10px] text-slate-400">Dự kiến đón</p>
          </div>
        </div>

        {/* Driver Details */}
        {activeTrip.driver && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src={activeTrip.driver.avatar}
                alt={activeTrip.driver.name}
                className="w-12 h-12 rounded-full object-cover ring-2 ring-[#00A699]/30"
              />
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-white">
                  {activeTrip.driver.name}
                </p>
                <p className="text-[11px] font-extrabold text-[#00A699]">
                  {activeTrip.driver.licensePlate}
                </p>
                <p className="text-[10px] text-slate-400">{activeTrip.driver.vehicleName}</p>
              </div>
            </div>

            {/* Quick Contact Buttons */}
            <div className="flex items-center gap-2">
              <a
                href={`tel:${activeTrip.driver.phone}`}
                className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-50 text-[#00A699] dark:bg-[#00A699]/20 hover:scale-105 transition"
                aria-label="Gọi tài xế"
              >
                <Phone className="w-4 h-4" />
              </a>
              <button
                type="button"
                onClick={openAssistant}
                className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-50 text-cyan-600 dark:bg-cyan-950/40 hover:scale-105 transition cursor-pointer"
                aria-label="Nhắn tin qua trợ lý"
              >
                <MessageSquare className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Route Details */}
        <div className="rounded-xl p-2.5 bg-slate-50 dark:bg-white/5 text-[11px] space-y-1.5">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
            <span className="w-2 h-2 rounded-full bg-[#00A699] shrink-0" />
            <span className="truncate font-semibold">{activeTrip.pickup}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
            <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
            <span className="truncate font-semibold">{activeTrip.destination}</span>
          </div>
        </div>

        {/* Safety Note */}
        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-[#00A699]" />
            Chuyến xe thuần điện an toàn 100%
          </span>
          <button
            type="button"
            onClick={openAssistant}
            className="text-[#00A699] font-bold flex items-center gap-0.5 cursor-pointer"
          >
            <Sparkles className="w-3 h-3" /> Nói với Trợ lý
          </button>
        </div>
      </div>
    </div>
  );
};
