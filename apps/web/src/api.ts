import type {
  AnalyticsResponse,
  ApiErrorPayload,
  DemoStatus,
  Journey,
  PlateSearchResponse,
  PlateSearchStatus,
  VehicleSummary,
} from "./api.generated";

export const actors = [
  "administrator",
  "investigator",
  "viewer",
  "approver",
] as const;

export type Actor = (typeof actors)[number];

export interface AuthSession {
  readonly actor: Actor;
  readonly mode: "local_demo";
}

export interface LoginRequest {
  readonly actor: Actor;
  readonly password: string;
}

export interface HealthResponse {
  readonly status: "ready";
}

export interface LogoutResponse {
  readonly logged_out: true;
}

export interface RequestOptions {
  readonly signal?: AbortSignal;
}

export interface VehicleQuery {
  readonly q?: string;
  readonly multiCameraOnly?: boolean;
  readonly limit?: number;
}

export interface PlateQuery {
  readonly q: string;
  readonly limit?: number;
}

export type FetchImplementation = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export interface RoadEyeApiOptions {
  readonly baseUrl?: string;
  readonly fetch?: FetchImplementation;
  readonly onSessionExpired?: () => void;
}

export class RoadEyeApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, statusText: string, detail: unknown) {
    super(apiErrorMessage(status, statusText, detail));
    this.name = "RoadEyeApiError";
    this.status = status;
    this.detail = detail;
  }
}

function apiErrorMessage(
  status: number,
  statusText: string,
  detail: unknown,
): string {
  if (typeof detail === "string" && detail.trim()) {
    return `RoadEye API request failed (${status}): ${detail}`;
  }
  return `RoadEye API request failed (${status}): ${statusText || "Unknown error"}`;
}

function normalizeBaseUrl(value: string | undefined): string {
  return (value ?? "").replace(/\/+$/, "");
}

function boundedInteger(
  value: number | undefined,
  fallback: number,
  minimum: number,
  maximum: number,
  label: string,
): number {
  const selected = value ?? fallback;
  if (!Number.isInteger(selected) || selected < minimum || selected > maximum) {
    throw new RangeError(`${label} must be an integer from ${minimum} to ${maximum}`);
  }
  return selected;
}

function nonNegativeInteger(value: number, label: string): number {
  if (!Number.isInteger(value) || value < 0) {
    throw new RangeError(`${label} must be a non-negative integer`);
  }
  return value;
}

function encodedGlobalId(globalId: string): string {
  if (!globalId) throw new TypeError("globalId must not be empty");
  return encodeURIComponent(globalId);
}

function evidenceUrl(
  globalId: string,
  visitIndex: number,
  sampleIndex: number,
  kind: "crop" | "frame",
): string {
  return (
    `/api/vehicles/${encodedGlobalId(globalId)}/visits/` +
    `${nonNegativeInteger(visitIndex, "visitIndex")}/samples/` +
    `${nonNegativeInteger(sampleIndex, "sampleIndex")}/${kind}`
  );
}

async function responsePayload(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorDetail(payload: unknown): unknown {
  if (payload && typeof payload === "object" && "detail" in payload) {
    return (payload as ApiErrorPayload).detail;
  }
  return payload;
}

export function isSessionRequiredError(error: unknown): boolean {
  return (
    error instanceof RoadEyeApiError &&
    error.status === 401 &&
    error.detail === "SESSION_REQUIRED"
  );
}

export function createRoadEyeApi(options: RoadEyeApiOptions = {}) {
  const baseUrl = normalizeBaseUrl(options.baseUrl);
  const fetchRequest: FetchImplementation =
    options.fetch ?? ((input, init) => globalThis.fetch(input, init));

  async function requestJson<T>(
    method: "GET" | "POST",
    path: string,
    request: RequestOptions = {},
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetchRequest(`${baseUrl}${path}`, {
      method,
      credentials: "same-origin",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: request.signal,
    });
    const payload = await responsePayload(response);
    if (!response.ok) {
      const detail = errorDetail(payload);
      if (response.status === 401 && detail === "SESSION_REQUIRED") {
        options.onSessionExpired?.();
      }
      throw new RoadEyeApiError(response.status, response.statusText, detail);
    }
    if (payload === null) {
      throw new RoadEyeApiError(
        response.status,
        response.statusText,
        "Expected a JSON response",
      );
    }
    return payload as T;
  }

  return Object.freeze({
    health(request?: RequestOptions): Promise<HealthResponse> {
      return requestJson("GET", "/api/health", request);
    },

    login(body: LoginRequest, request?: RequestOptions): Promise<AuthSession> {
      return requestJson("POST", "/api/auth/login", request, body);
    },

    me(request?: RequestOptions): Promise<AuthSession> {
      return requestJson("GET", "/api/auth/me", request);
    },

    logout(request?: RequestOptions): Promise<LogoutResponse> {
      return requestJson("POST", "/api/auth/logout", request);
    },

    status(request?: RequestOptions): Promise<DemoStatus> {
      return requestJson("GET", "/api/status", request);
    },

    vehicles(
      query: VehicleQuery = {},
      request?: RequestOptions,
    ): Promise<readonly VehicleSummary[]> {
      const parameters = new URLSearchParams({
        q: query.q ?? "",
        multi_camera_only: String(query.multiCameraOnly ?? true),
        limit: String(boundedInteger(query.limit, 50, 1, 100, "limit")),
      });
      return requestJson("GET", `/api/vehicles?${parameters}`, request);
    },

    analytics(request?: RequestOptions): Promise<AnalyticsResponse> {
      return requestJson("GET", "/api/analytics", request);
    },

    plateSearchStatus(request?: RequestOptions): Promise<PlateSearchStatus> {
      return requestJson("GET", "/api/plate-search/status", request);
    },

    searchPlates(
      query: PlateQuery,
      request?: RequestOptions,
    ): Promise<PlateSearchResponse> {
      const parameters = new URLSearchParams({
        q: query.q,
        limit: String(boundedInteger(query.limit, 25, 1, 100, "limit")),
      });
      return requestJson("GET", `/api/plate-search?${parameters}`, request);
    },

    journey(globalId: string, request?: RequestOptions): Promise<Journey> {
      return requestJson(
        "GET",
        `/api/vehicles/${encodedGlobalId(globalId)}`,
        request,
      );
    },

    evidenceCropUrl(
      globalId: string,
      visitIndex: number,
      sampleIndex: number,
    ): string {
      return `${baseUrl}${evidenceUrl(globalId, visitIndex, sampleIndex, "crop")}`;
    },

    evidenceFrameUrl(
      globalId: string,
      visitIndex: number,
      sampleIndex: number,
    ): string {
      return `${baseUrl}${evidenceUrl(globalId, visitIndex, sampleIndex, "frame")}`;
    },
  });
}

export type RoadEyeApi = ReturnType<typeof createRoadEyeApi>;

type SessionExpiredListener = () => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

export function subscribeToSessionExpiry(
  listener: SessionExpiredListener,
): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

export const api: RoadEyeApi = createRoadEyeApi({
  onSessionExpired: () => {
    for (const listener of sessionExpiredListeners) listener();
  },
});
