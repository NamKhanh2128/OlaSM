import React, { useState } from "react";
import {
  ArrowDownUp,
  CheckCircle2,
  Clock,
  CreditCard,
  Mic,
  ShieldCheck,
  Sparkles,
  Ticket,
  Users,
  Zap,
} from "lucide-react";
import { MOCK_SERVICES_CATALOG } from "@/features/booking/mockData";
import { useVoiceAssistant } from "@/features/ai-assistant/context/useVoiceAssistant";

export const BookingPage: React.FC = () => {
  const { openWithPrefill } = useVoiceAssistant();
  const [pickup, setPickup] = useState("72 Lê Thánh Tôn, Bến Nghé, Q.1, TP.HCM");
  const [destination, setDestination] = useState("Vincom Landmark 81, P.22, Bình Thạnh");
  const [selectedVehicle, setSelectedVehicle] = useState<string>("CAR_4");

  const swapLocations = () => {
    const temp = pickup;
    setPickup(destination);
    setDestination(temp);
  };

  const currentVehicleObj = MOCK_SERVICES_CATALOG.find((v) => v.id === selectedVehicle) || MOCK_SERVICES_CATALOG[1];

  const handleVoiceOrder = () => {
    openWithPrefill(`Tôi muốn đặt ${currentVehicleObj.name} từ ${pickup} đến ${destination}.`);
  };

  return (
    <div className="space-y-4 pb-6">
      {/* Route Selector Card (Điểm đón & Điểm đến) */}
      <div className="rounded-2xl p-3.5 bg-white dark:bg-[#152026] border border-slate-200/80 dark:border-white/10 shadow-sm">
        <div className="flex items-center gap-3">
          {/* Vertical Dots Indicator */}
          <div className="flex flex-col items-center gap-1 shrink-0 py-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#00A699] ring-2 ring-[#00A699]/20" />
            <span className="w-0.5 h-6 bg-slate-200 dark:bg-slate-700" />
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500 ring-2 ring-rose-500/20" />
          </div>

          {/* Inputs */}
          <div className="flex-1 space-y-2 min-w-0">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Điểm đón</p>
              <input
                type="text"
                value={pickup}
                onChange={(e) => setPickup(e.target.value)}
                className="w-full text-xs font-semibold text-slate-800 dark:text-slate-100 bg-transparent outline-none truncate"
                placeholder="Nhập điểm đón..."
              />
            </div>
            <div className="border-t border-slate-100 dark:border-white/5 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Điểm đến</p>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full text-xs font-semibold text-slate-800 dark:text-slate-100 bg-transparent outline-none truncate"
                placeholder="Nhập điểm đến..."
              />
            </div>
          </div>

          {/* Swap Button */}
          <button
            type="button"
            onClick={swapLocations}
            className="grid h-8 w-8 place-items-center rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/10 dark:hover:bg-white/15 text-slate-600 dark:text-slate-300 transition shrink-0"
            aria-label="Đổi chiều điểm đón và điểm đến"
          >
            <ArrowDownUp className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Fleet Selector (Danh sách xe thuần điện Green SM) */}
      <div>
        <div className="flex items-center justify-between mb-2 px-1">
          <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Chọn xe điện VinFast
          </h2>
          <span className="text-[11px] text-[#00A699] font-bold flex items-center gap-1">
            <Zap className="w-3 h-3" /> 100% Thuần điện
          </span>
        </div>

        <div className="space-y-2">
          {MOCK_SERVICES_CATALOG.map((service, idx) => {
            const isSelected = selectedVehicle === service.id;
            return (
              <div
                key={service.id}
                onClick={() => setSelectedVehicle(service.id)}
                className={`relative flex items-center gap-3 p-3 rounded-2xl cursor-pointer transition-all border ${
                  isSelected
                    ? "bg-[#E7FBF9] dark:bg-[#00A699]/15 border-[#00A699] ring-1 ring-[#00A699]"
                    : "bg-white dark:bg-[#152026] border-slate-200/70 dark:border-white/10 hover:border-slate-300"
                }`}
              >
                {/* Car Thumbnail */}
                <div className="h-14 w-16 shrink-0 rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-800 relative">
                  <img src={service.image} alt={service.name} className="h-full w-full object-cover" />
                  {service.badge && (
                    <span className="absolute top-1 left-1 px-1 py-0.2 rounded bg-amber-500 text-white text-[8px] font-bold">
                      {service.badge}
                    </span>
                  )}
                </div>

                {/* Details */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-extrabold text-slate-900 dark:text-white truncate">
                      {service.name}
                    </p>
                    <p className="text-xs font-extrabold text-[#00A699] dark:text-[#00E5C9]">
                      {service.startingPrice}
                    </p>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-400">
                    <span className="flex items-center gap-0.5">
                      <Clock className="w-3 h-3" /> {2 + idx} phút tới
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-0.5">
                      <Users className="w-3 h-3" /> {service.features[0]?.label}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                    {service.description}
                  </p>
                </div>

                {/* Selection Radio */}
                <div className="shrink-0 pl-1">
                  {isSelected ? (
                    <CheckCircle2 className="w-5 h-5 text-[#00A699] fill-[#00A699]/20" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-slate-300 dark:border-slate-600" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Payment & Voucher Strip */}
      <div className="rounded-2xl p-3 bg-white dark:bg-[#152026] border border-slate-200/80 dark:border-white/10 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-[#00A699]" />
          <div>
            <p className="font-bold text-slate-800 dark:text-white text-[11px]">Ví Xanh Pay</p>
            <p className="text-[10px] text-slate-400">Số dư: 250.000đ</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 text-[10px] font-bold border border-amber-200/60 dark:border-amber-800/30">
          <Ticket className="w-3 h-3" />
          <span>Giảm 15.000đ</span>
        </div>
      </div>

      {/* Primary Action Button (Voice Order Shortcut) */}
      <div className="space-y-2 pt-1">
        <button
          type="button"
          onClick={handleVoiceOrder}
          className="w-full flex items-center justify-center gap-2 py-3.5 px-4 rounded-2xl bg-gradient-to-r from-[#00A699] to-[#00C9B7] text-white font-extrabold text-xs shadow-lg shadow-[#00A699]/25 hover:scale-[1.01] active:scale-[0.99] transition cursor-pointer"
        >
          <Mic className="w-4 h-4" />
          <span>Nói để đặt {currentVehicleObj.name} ngay</span>
          <Sparkles className="w-4 h-4 text-[#E7FBF9]" />
        </button>

        <p className="text-center text-[10px] text-slate-400 flex items-center justify-center gap-1">
          <ShieldCheck className="w-3 h-3 text-[#00A699]" />
          Bảo hiểm chuyến đi Green SM tự động kích hoạt
        </p>
      </div>
    </div>
  );
};