export const BOOKING_CREATED_EVENT = "olasm:booking-created";
export const LEGACY_BOOKING_CREATED_EVENT = "alosm:booking-created";

export function notifyBookingCreated(bookingId: string): void {
  window.dispatchEvent(
    new CustomEvent(BOOKING_CREATED_EVENT, {
      detail: { booking_id: bookingId },
    }),
  );
  window.dispatchEvent(
    new CustomEvent(LEGACY_BOOKING_CREATED_EVENT, {
      detail: { booking_id: bookingId },
    }),
  );
}

