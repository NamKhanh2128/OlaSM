import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BookingProgressStrip } from "./BookingProgressStrip";

describe("BookingProgressStrip", () => {
  it("does not render before booking data exists", () => {
    const { container } = render(<BookingProgressStrip progress={null} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows resolved values and the next missing slot", () => {
    render(
      <BookingProgressStrip
        progress={{
          pickup: { label: "VinUni", resolved: true, place_id: "vinuni" },
          destination: { label: "Hồ Gươm", resolved: true, place_id: "ho-guom" },
          vehicle_type: null,
          missing_field: "vehicle_type",
          fare_amount: null,
          currency: "VND",
        }}
      />,
    );

    expect(screen.getByText("VinUni")).toBeInTheDocument();
    expect(screen.getByText("Hồ Gươm")).toBeInTheDocument();
    expect(screen.getByText("Đang chờ…")).toBeInTheDocument();
  });

  it("uses the customer-facing vehicle label", () => {
    render(
      <BookingProgressStrip
        progress={{
          pickup: null,
          destination: null,
          vehicle_type: "CAR_4",
          missing_field: null,
          fare_amount: null,
          currency: "VND",
        }}
      />,
    );

    expect(screen.getByText("Ô tô 4 chỗ")).toBeInTheDocument();
  });
});
