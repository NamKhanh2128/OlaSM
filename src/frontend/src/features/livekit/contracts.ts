export const BOOKING_STATE_TOPIC = "alosm.booking_state.v1";

export type PlaceState = {
  place_id: string;
  display_name: string;
  address: string;
  provider: string;
  city?: string | null;
};

export type QuoteState = {
  quote_id: string;
  fare_amount: number;
  currency: string;
  distance_km: number;
  eta_minutes: number;
  estimated: boolean;
};

export type BookingResultState = {
  booking_id: string;
  status: string;
  estimated_fare: number;
  currency: string;
  eta_minutes: number;
};

export type VoiceFailureState = {
  code: string;
  message: string;
  retryable: boolean;
  fallback_action: "repeat_or_text" | "retry" | "handoff" | "none";
};

export type HandoffState = {
  handoff_id: string;
  status: "pending" | "accepted" | "connected" | "resolved" | "failed";
  reason_code: string;
};

export type PostBookingSupportState = {
  booking_id: string;
  stage: "menu" | "driver_request_sent" | "tracking" | "rating_requested" | "restart_requested";
  last_driver_request: string | null;
  driver_request_count: number;
  eta_minutes: number;
  distance_to_pickup_km: number;
  elapsed_minutes: number;
};

export type ClarificationTarget = "pickup" | "destination" | "vehicle_type";
export type BookingSlotKey = ClarificationTarget;
export type BookingSlotStatus = "missing" | "needs_clarification" | "resolved";

export type BookingClarificationState = {
  clarification_id: string;
  target: ClarificationTarget;
  query: string | null;
  selected_index?: number | null;
  options: Array<{
    index: number;
    value?: string;
    display_name: string;
    subtitle: string;
  }>;
};

export type BookingState = {
  schema_version: "1";
  revision: number;
  pickup: PlaceState | null;
  destination: PlaceState | null;
  vehicle_type: "MOTORBIKE" | "CAR_4" | "CAR_7" | "LUXURY" | null;
  quote: QuoteState | null;
  confirmation_status: "not_requested" | "awaiting" | "confirmed";
  cancellation_confirmation_pending?: boolean;
  booking: BookingResultState | null;
  failure?: VoiceFailureState | null;
  handoff?: HandoffState | null;
  recovered?: boolean;
  post_booking_support?: PostBookingSupportState | null;
  slot_statuses?: Record<BookingSlotKey, BookingSlotStatus>;
  slot_labels?: Record<BookingSlotKey, string | null>;
  next_required_field?: BookingSlotKey | null;
  all_required_slots_resolved?: boolean;
  pending_place_clarification?: BookingClarificationState | null;
  clarifications?: {
    pickup: BookingClarificationState | null;
    destination: BookingClarificationState | null;
    vehicle_type: BookingClarificationState | null;
  };
};
