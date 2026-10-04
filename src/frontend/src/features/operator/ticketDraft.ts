/**
 * Ticket draft state management for operator desk.
 * Adapted from donor web-v2 with strict adherence to OlaSM canonical contracts.
 */

export interface CandidatePlace {
  place_id: string;
  display_name: string;
  lat?: number;
  lng?: number;
}

export interface SlotDraft {
  query: string;
  candidates: CandidatePlace[];
  selected: CandidatePlace | null;
  confirmedWithCustomer: boolean;
  searching: boolean;
}

export interface TicketDraftState {
  pickup: SlotDraft;
  destination: SlotDraft;
  vehicleType: string | null;
  estimatedFare: number | null;
  notes: string;
}

export function createEmptySlot(initialQuery = ""): SlotDraft {
  return {
    query: initialQuery,
    candidates: [],
    selected: null,
    confirmedWithCustomer: false,
    searching: false,
  };
}

export function createInitialTicketDraft(
  initialPickup?: string,
  initialDestination?: string,
  vehicleType?: string
): TicketDraftState {
  return {
    pickup: createEmptySlot(initialPickup || ""),
    destination: createEmptySlot(initialDestination || ""),
    vehicleType: vehicleType || "CAR_4",
    estimatedFare: null,
    notes: "",
  };
}

export function selectCandidate(slot: SlotDraft, candidate: CandidatePlace): SlotDraft {
  const isSame = slot.selected?.place_id === candidate.place_id;
  return {
    ...slot,
    selected: candidate,
    query: candidate.display_name,
    confirmedWithCustomer: isSame ? slot.confirmedWithCustomer : false,
  };
}

export function setSlotConfirmation(slot: SlotDraft, confirmed: boolean): SlotDraft {
  if (!slot.selected) {
    return { ...slot, confirmedWithCustomer: false };
  }
  return { ...slot, confirmedWithCustomer: confirmed };
}
