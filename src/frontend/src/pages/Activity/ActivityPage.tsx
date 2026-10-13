import React, { useState } from "react";
import { ActivityList } from "@/features/activity/components/ActivityList";

export const ActivityPage: React.FC = () => {
  const [filter, setFilter] = useState<string>("all");

  const filterChips = [
    { id: "all", label: "Tất cả" },
    { id: "recent", label: "Gần đây" },
    { id: "last_month", label: "Tháng trước" },
    { id: "cancelled", label: "Đã hủy" },
  ];

  return (
    <div className="w-full space-y-3 pb-6">
      <h1 className="text-lg font-extrabold text-[#191C1E] dark:text-white tracking-tight">
        Hoạt động & Chuyến đi
      </h1>

      <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1">
        {filterChips.map((chip) => {
          const isActive = filter === chip.id;
          return (
            <button
              key={chip.id}
              onClick={() => setFilter(chip.id)}
              className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
                isActive
                  ? "bg-[#00A699] text-white shadow-sm"
                  : "bg-white text-slate-700 hover:bg-[#E7FBF9] dark:bg-white/10 dark:text-slate-300 border border-slate-200/60 dark:border-white/10"
              }`}
            >
              {chip.label}
            </button>
          );
        })}
      </div>

      <ActivityList activeFilter={filter} />
    </div>
  );
};
