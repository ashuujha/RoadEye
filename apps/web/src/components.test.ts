import { describe, expect, it } from "vitest";
import { display } from "./display";

describe("Display formatting and truth rules", () => {
  it("distinguishes null/undefined missing coverage from zero", () => {
    expect(display(null)).toBe("Not available");
    expect(display(undefined)).toBe("Not available");
    expect(display(0)).toBe("0");
    expect(display(0.0)).toBe("0");
    expect(display(0.1234)).toBe("0.123");
  });

  it("handles string and object values gracefully", () => {
    expect(display("DL01AA1234")).toBe("DL01AA1234");
    expect(display({ camera: "C1" })).toBe('{"camera":"C1"}');
  });
});

describe("Status categorization", () => {
  const getCategory = (status: string | null | undefined) => {
    if (!status) return "neutral";
    const s = status.toLowerCase();
    if (["accepted", "observed", "fresh", "done", "plausible", "approved", "valid", "correct"].includes(s)) {
      return "success";
    }
    if (["review_required", "ambiguous", "stale", "leased", "uncertain", "partial"].includes(s)) {
      return "warning";
    }
    if (["rejected", "poison", "error", "failed", "revoked", "incorrect", "missing"].includes(s)) {
      return "danger";
    }
    if (["inferred", "playing"].includes(s)) {
      return "info";
    }
    return "neutral";
  };

  it("classifies confirmed and accepted states as success", () => {
    expect(getCategory("accepted")).toBe("success");
    expect(getCategory("observed")).toBe("success");
    expect(getCategory("done")).toBe("success");
  });

  it("classifies uncertainty and review states as warning", () => {
    expect(getCategory("review_required")).toBe("warning");
    expect(getCategory("uncertain")).toBe("warning");
    expect(getCategory("ambiguous")).toBe("warning");
  });

  it("classifies rejection and errors as danger", () => {
    expect(getCategory("rejected")).toBe("danger");
    expect(getCategory("error")).toBe("danger");
    expect(getCategory("revoked")).toBe("danger");
  });

  it("classifies inferred routes as info", () => {
    expect(getCategory("inferred")).toBe("info");
  });
});
