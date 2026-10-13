import React from "react";
import { NavLink } from "react-router-dom";
import { Car, Clock, Gift, Headphones, Home, User } from "lucide-react";
import { cn } from "@/utils/cn";
import { getUserRole } from "@/features/auth/storage";

const customerMobileTabs = [
  { path: "/", label: "Trang chủ", icon: Home },
  { path: "/booking", label: "Đặt xe", icon: Car },
  { path: "/activity", label: "Hoạt động", icon: Clock },
  { path: "/payment", label: "Ưu đãi", icon: Gift },
  { path: "/profile", label: "Tài khoản", icon: User },
];

export const MobileNav: React.FC = () => {
  const isOperator = getUserRole() === "OPERATOR" || getUserRole() === "ADMIN";
  const tabs = isOperator
    ? [
        { path: "/", label: "Trang chủ", icon: Home },
        { path: "/booking", label: "Đặt xe", icon: Car },
        { path: "/activity", label: "Hoạt động", icon: Clock },
        { path: "/operator", label: "Tổng đài", icon: Headphones },
        { path: "/profile", label: "Tài khoản", icon: User },
      ]
    : customerMobileTabs;

  return (
    <nav
      aria-label="Điều hướng chính"
      className="shrink-0 h-[64px] px-2 bg-white/95 dark:bg-[#12191F]/95 backdrop-blur-xl border-t border-slate-200/80 dark:border-white/10 flex items-center justify-around z-30"
    >
      {tabs.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              cn(
                "flex-1 flex flex-col items-center justify-center py-1.5 transition-all duration-200 cursor-pointer",
                isActive
                  ? "text-[#00A699] dark:text-[#00C9B7] font-bold"
                  : "text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 font-medium"
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className={cn("relative p-1 rounded-xl transition-all", isActive && "bg-[#E7FBF9] dark:bg-[#00C9B7]/15")}>
                  <Icon className={cn("w-5 h-5", isActive ? "stroke-[2.5px]" : "stroke-[1.8px]")} />
                  {isActive && (
                    <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#00A699] dark:bg-[#00C9B7]" />
                  )}
                </div>
                <span className="text-[10px] mt-0.5 tracking-tight">{item.label}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};
