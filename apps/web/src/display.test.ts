import { expect, test } from "vitest";
import { display } from "./display";
test("missing coverage is distinct from observed zero", () => {
  expect(display(null)).toBe("Not available");
  expect(display(0)).toBe("0");
  expect(display(0.5)).toBe("0.500");
});
