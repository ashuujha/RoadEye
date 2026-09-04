export function display(value: unknown): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value === "number")
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
