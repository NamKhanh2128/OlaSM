import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bike,
  Car,
  ChevronRight,
  Gift,
  Leaf,
  MapPin,
  Package,
  Search,
  Sparkles,
} from "lucide-react";
import { listBookings, locationLabel, type BookingSummary } from "@/features/activity/api";
import { redirectToLoginIfUnauthorized } from "@/features/auth/sessionGuard";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";

const quickPrompts = [
  "Đặt Xanh SM Taxi đến Vincom Landmark 81",
  "Đặt xe máy điện VinFast về nhà",
  "Tìm xe Xanh SM Luxury 4 chỗ",
  "Tài xế của tôi đang ở đâu?",
];

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { openWithPrefill, open } = useVoiceAssistant();
  const [recentBookings, setRecentBookings] = useState<BookingSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    listBookings()
      .then((data) => !cancelled && setRecentBookings(data.slice(0, 2)))
      .catch((cause) => {
        if (!cancelled) redirectToLoginIfUnauthorized(cause, navigate);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return (
    <div className="space-y-4 pb-6">
      {/* Green SM Loyalty & Wallet Bar */}
      <div className="rounded-2xl p-3.5 bg-gradient-to-r from-[#00A699] to-[#008F88] text-white shadow-md shadow-[#00A699]/15">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-white/20 text-white">
              <Leaf className="h-3.5 w-3.5" />
            </span>
            <span className="font-bold">Xanh Club • Hạng Vàng</span>
          </div>
          <span className="text-[11px] font-semibold bg-white/20 px-2 py-0.5 rounded-full">
            1.250 điểm
          </span>
        </div>
        <div className="mt-2.5 pt-2 border-t border-white/15 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-white/80 uppercase tracking-wider">Số dư Xanh Pay</p>
            <p className="text-sm font-extrabold">250.000 đ</p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/payment")}
            className="text-[11px] font-bold bg-white text-[#008F88] px-3 py-1 rounded-xl shadow-sm hover:bg-slate-50 transition cursor-pointer"
          >
            Nạp tiền
          </button>
        </div>
      </div>

      {/* Voice Assistant Search Bar */}
      <div className="space-y-2">
        <button
          type="button"
          onClick={open}
          className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/80 dark:border-white/10 shadow-sm text-left hover:border-[#00A699] transition-all group cursor-pointer"
        >
          <Search className="h-5 w-5 text-[#00A699] shrink-0" />
          <span className="flex-1 text-xs font-semibold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 truncate">
            Bạn muốn đi đâu hôm nay?
          </span>
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-tr from-[#00A699] to-[#00C9B7] text-white shadow-sm shrink-0">
            <Sparkles className="h-4 w-4" />
          </span>
        </button>

        {/* Quick Voice Prompts Horizontal Scroll */}
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar py-0.5">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => openWithPrefill(prompt)}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-white dark:bg-[#152026] border border-slate-200/60 dark:border-white/5 text-[11px] font-medium text-slate-600 dark:text-slate-300 hover:text-[#00A699] hover:border-[#00A699]/40 transition cursor-pointer"
            >
              <span className="text-[#00A699]">🗣️</span>
              <span className="truncate max-w-[200px]">{prompt}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Green SM 4 Core Services */}
      <div>
        <div className="flex items-center justify-between mb-2 px-1">
          <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Dịch vụ Xanh SM
          </h2>
          <button
            type="button"
            onClick={() => navigate("/booking")}
            className="text-[11px] font-bold text-[#00A699] flex items-center cursor-pointer"
          >
            Tất cả <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {/* Xanh SM Taxi */}
          <button
            type="button"
            onClick={() => navigate("/booking")}
            className="p-3 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-left hover:border-[#00A699]/50 transition shadow-sm group cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-[#00A699]">
                <Car className="h-5 w-5" />
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
                VF 5 / e34
              </span>
            </div>
            <p className="mt-2 text-xs font-extrabold text-slate-800 dark:text-white group-hover:text-[#00A699]">
              Xanh SM Taxi
            </p>
            <p className="text-[10px] text-slate-400">4 chỗ • Không mùi</p>
          </button>

          {/* Xanh SM Luxury */}
          <button
            type="button"
            onClick={() => navigate("/booking")}
            className="p-3 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-left hover:border-[#00A699]/50 transition shadow-sm group cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600">
                <Car className="h-5 w-5" />
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300">
                VF 8 VIP
              </span>
            </div>
            <p className="mt-2 text-xs font-extrabold text-slate-800 dark:text-white group-hover:text-cyan-600">
              Xanh SM Luxury
            </p>
            <p className="text-[10px] text-slate-400">Thương gia 5 sao</p>
          </button>

          {/* Xanh SM Bike */}
          <button
            type="button"
            onClick={() => navigate("/booking")}
            className="p-3 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-left hover:border-[#00A699]/50 transition shadow-sm group cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-50 dark:bg-teal-950/40 text-teal-600">
                <Bike className="h-5 w-5" />
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300">
                Feliz S
              </span>
            </div>
            <p className="mt-2 text-xs font-extrabold text-slate-800 dark:text-white group-hover:text-teal-600">
              Xanh SM Bike
            </p>
            <p className="text-[10px] text-slate-400">Xe máy điện nội thành</p>
          </button>

          {/* Xanh Express */}
          <button
            type="button"
            onClick={() => openWithPrefill("Tôi muốn đặt dịch vụ giao hàng Xanh Express.")}
            className="p-3 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-left hover:border-[#00A699]/50 transition shadow-sm group cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-600">
                <Package className="h-5 w-5" />
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                Siêu tốc
              </span>
            </div>
            <p className="mt-2 text-xs font-extrabold text-slate-800 dark:text-white group-hover:text-amber-600">
              Xanh Express
            </p>
            <p className="text-[10px] text-slate-400">Giao hàng xe điện</p>
          </button>
        </div>
      </div>

      {/* Live Radar Mini-Map Widget (Mô phỏng vị trí xe điện quanh bạn) */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-200/80 dark:border-white/10 bg-slate-900 text-white shadow-sm">
        {/* Map Canvas Background */}
        <div className="h-32 w-full bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:14px_14px] bg-[#0f172a] relative flex items-center justify-center overflow-hidden">
          {/* Radar Circles */}
          <div className="absolute w-44 h-44 rounded-full border border-[#00A699]/20" />
          <div className="absolute w-28 h-28 rounded-full border border-[#00A699]/30" />
          <div className="absolute w-14 h-14 rounded-full bg-[#00A699]/15 animate-ping" />

          {/* User Location Pin */}
          <div className="relative z-10 flex flex-col items-center">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-[#00A699] text-white shadow-lg ring-2 ring-white">
              <MapPin className="h-4 w-4" />
            </span>
            <span className="mt-1 text-[9px] font-bold bg-black/70 px-1.5 py-0.5 rounded backdrop-blur">
              Bạn ở đây
            </span>
          </div>

          {/* Surrounding Electric Vehicles */}
          <div className="absolute top-4 left-10 flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded-full text-[9px] border border-white/10">
            <Car className="w-3 h-3 text-[#00E5C9]" />
            <span>VF e34 • 2m</span>
          </div>
          <div className="absolute bottom-5 right-8 flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded-full text-[9px] border border-white/10">
            <Car className="w-3 h-3 text-cyan-400" />
            <span>VF 8 • 4m</span>
          </div>
          <div className="absolute top-6 right-12 flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded-full text-[9px] border border-white/10">
            <Bike className="w-3 h-3 text-emerald-400" />
            <span>Feliz S • 1m</span>
          </div>
        </div>

        {/* Radar Map Bottom Bar */}
        <div className="p-2.5 bg-slate-800/90 backdrop-blur-md flex items-center justify-between text-xs">
          <div>
            <p className="font-bold text-white text-[11px]">Đang có 5 xe VinFast quanh bạn</p>
            <p className="text-[10px] text-slate-400">Thời gian đón trung bình: 2-3 phút</p>
          </div>
          <button
            type="button"
            onClick={() => openWithPrefill("Tôi muốn đặt xe ngay bây giờ.")}
            className="px-3 py-1.5 rounded-xl bg-[#00A699] text-white font-bold text-[11px] shadow-sm hover:bg-[#008F88] transition cursor-pointer"
          >
            Đặt xe ngay
          </button>
        </div>
      </div>

      {/* Promo Banner VinFast GSM */}
      <div className="rounded-2xl p-3.5 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 border border-emerald-200/60 dark:border-emerald-800/30">
        <div className="flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-[#00A699] text-white shrink-0">
            <Gift className="h-3.5 w-3.5" />
          </span>
          <p className="text-xs font-bold text-slate-800 dark:text-slate-100">
            Ưu đãi 50% cho chuyến đi bằng giọng nói
          </p>
        </div>
        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
          Nói với Trợ lý ảo để áp dụng mã giảm giá GSM độc quyền hôm nay.
        </p>
      </div>

      {/* Recent Trips */}
      <div>
        <div className="flex items-center justify-between mb-2 px-1">
          <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Chuyến gần đây
          </h2>
          <button
            type="button"
            onClick={() => navigate("/activity")}
            className="text-[11px] font-bold text-[#00A699] cursor-pointer"
          >
            Lịch sử
          </button>
        </div>

        <div className="space-y-2">
          {recentBookings.length ? (
            recentBookings.map((booking) => (
              <button
                key={booking.booking_id}
                type="button"
                onClick={() =>
                  openWithPrefill(
                    `Đặt lại chuyến đến ${locationLabel(booking.destination, "điểm đến cũ")}.`
                  )
                }
                className="w-full flex items-center gap-3 p-3 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-left hover:border-[#00A699]/40 transition shadow-sm cursor-pointer"
              >
                <span className="grid h-8 w-8 place-items-center rounded-xl bg-slate-100 dark:bg-white/10 text-[#00A699] shrink-0">
                  <MapPin className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-slate-800 dark:text-white truncate">
                    {locationLabel(booking.destination, "Điểm đến")}
                  </p>
                  <p className="text-[10px] text-slate-400 truncate">
                    {locationLabel(booking.pickup, "Điểm đón")}
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400 shrink-0" />
              </button>
            ))
          ) : (
            <div className="p-4 rounded-2xl bg-white dark:bg-[#152026] border border-slate-200/70 dark:border-white/10 text-center text-xs text-slate-400">
              Chưa có chuyến gần đây. Hãy nói để đặt chuyến xe đầu tiên!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};