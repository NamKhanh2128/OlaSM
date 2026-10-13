import { Users, Snowflake, Wifi, Zap } from "lucide-react";

// Danh mục minh họa đồng bộ bốn VehicleType của Core Agent. Giá chỉ là DEMO;
// quote xác nhận booking luôn phải lấy từ backend catalog có version.
export interface ServiceOptionItem {
  id: "MOTORBIKE" | "CAR_4" | "CAR_7" | "LUXURY";
  name: string;
  badge?: string;
  description: string;
  startingPrice: string;
  basePrice: number;
  features: {
    icon: any;
    label: string;
  }[];
  image: string;
}

export const MOCK_SERVICES_CATALOG: ServiceOptionItem[] = [
  {
    id: "MOTORBIKE",
    name: "Xanh SM Bike",
    description: "Xe máy điện VinFast Feliz S / Evo 200 — Len lỏi giờ cao điểm, êm ái, 0 phát thải.",
    startingPrice: "13.800đ",
    basePrice: 13800,
    features: [
      { icon: Users, label: "1 Chỗ" },
      { icon: Zap, label: "VinFast Feliz S / Evo 200" },
    ],
    image:
      "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=600&q=80",
  },
  {
    id: "CAR_4",
    name: "Xanh SM Taxi",
    description: "VinFast VF 5 Plus & VF e34 — Di chuyển xanh thông minh, không mùi xăng xe, êm ái.",
    startingPrice: "32.000đ",
    basePrice: 32000,
    features: [
      { icon: Users, label: "4 Chỗ" },
      { icon: Snowflake, label: "VinFast VF 5 / e34" },
    ],
    image:
      "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=600&q=80",
  },
  {
    id: "CAR_7",
    name: "Xanh SM Plus",
    description: "VinFast VF 9 / 7 chỗ cao cấp — Không gian thoáng đãng cho cả gia đình và hành lý.",
    startingPrice: "48.000đ",
    basePrice: 48000,
    features: [
      { icon: Users, label: "7 Chỗ" },
      { icon: Wifi, label: "VinFast VF 9 Rộng Rãi" },
    ],
    image:
      "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=600&q=80",
  },
  {
    id: "LUXURY",
    name: "Xanh SM Luxury",
    badge: "VIP",
    description: "VinFast VF 8 Thương Gia — Nội thất da cao cấp, tài xế chuyên nghiệp đạt chuẩn 5 sao.",
    startingPrice: "55.000đ",
    basePrice: 55000,
    features: [
      { icon: Users, label: "4 Chỗ VIP" },
      { icon: Snowflake, label: "VinFast VF 8 Luxury" },
    ],
    image:
      "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=600&q=80",
  },
];
