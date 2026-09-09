import createClient from "openapi-fetch";
import type { paths } from "./api.generated";

export const client = createClient<paths>({
  baseUrl: "",
  credentials: "include",
  headers: { "X-RoadEye": "console" },
});
export const key = () => ({ "Idempotency-Key": crypto.randomUUID() });
export function unwrap<T>({
  data,
  error,
  response,
}: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (!response.ok || data === undefined) {
    const detail = error as { error?: string } | undefined;
    throw new Error(
      `${response.status === 403 ? "Permission denied" : response.status === 401 ? "Sign in required" : "Request failed"} (${response.status}): ${detail?.error || response.statusText}`,
    );
  }
  return data;
}
