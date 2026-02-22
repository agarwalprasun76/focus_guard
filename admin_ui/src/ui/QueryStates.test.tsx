import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState, ErrorState, LoadingState, OfflineState } from "./QueryStates";

describe("QueryStates", () => {
  it("renders loading with polite status semantics", () => {
    render(<LoadingState label="dashboard" />);
    const node = screen.getByRole("status");
    expect(node).toHaveTextContent("Loading dashboard...");
    expect(node).toHaveAttribute("aria-live", "polite");
  });

  it("renders error with alert semantics", () => {
    render(<ErrorState message="Boom" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
  });

  it("renders empty and offline states", () => {
    render(
      <>
        <EmptyState message="Nothing here" />
        <OfflineState message="Offline" />
      </>
    );

    expect(screen.getAllByRole("status")).toHaveLength(2);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});
