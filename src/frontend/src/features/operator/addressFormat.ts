/**
 * Address formatting utilities for clean card/table display.
 * Adapted from donor web-v2.
 */

export function shortPlace(displayAddress: string): string {
  if (!displayAddress) return "";
  const parts = displayAddress
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) return displayAddress;
  const [head, second] = parts;
  if (second && head.length < 18) return `${head}, ${second}`;
  return head;
}

export function shortRoute(pickup: string, destination: string): string {
  if (!pickup && !destination) return "";
  if (!pickup) return shortPlace(destination);
  if (!destination) return shortPlace(pickup);
  return `${shortPlace(pickup)} ➔ ${shortPlace(destination)}`;
}
