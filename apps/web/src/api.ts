import type {
  AnalyticsResponse,
  ApiErrorPayload,
  DemoStatus,
  Journey,
  PlateSearchResponse,
  PlateSearchStatus,
  VehicleSummary,
} from "./api.generated";

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

export function createRoadEyeApi(options: RoadEyeApiOptions = {}) {
  const baseUrl = normalizeBaseUrl(options.baseUrl);
  const fetchRequest: FetchImplementation =
    options.fetch ?? ((input, init) => globalThis.fetch(input, init));

  async function getJson<T>(path: string, request: RequestOptions = {}): Promise<T> {
    const response = await fetchRequest(`${baseUrl}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: request.signal,
    });
    const payload = await responsePayload(response);
    if (!response.ok) {
      throw new RoadEyeApiError(
        response.status,
        response.statusText,
        errorDetail(payload),
      );
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
    status(request?: RequestOptions): Promise<DemoStatus> {
      return getJson("/api/status", request);
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
      return getJson(`/api/vehicles?${parameters}`, request);
    },

    analytics(request?: RequestOptions): Promise<AnalyticsResponse> {
      return getJson("/api/analytics", request);
    },

    plateSearchStatus(request?: RequestOptions): Promise<PlateSearchStatus> {
      return getJson("/api/plate-search/status", request);
    },

    searchPlates(
      query: PlateQuery,
      request?: RequestOptions,
    ): Promise<PlateSearchResponse> {
      const parameters = new URLSearchParams({
        q: query.q,
        limit: String(boundedInteger(query.limit, 25, 1, 100, "limit")),
      });
      return getJson(`/api/plate-search?${parameters}`, request);
    },

    journey(globalId: string, request?: RequestOptions): Promise<Journey> {
      return getJson(`/api/vehicles/${encodedGlobalId(globalId)}`, request);
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

export const api: RoadEyeApi = createRoadEyeApi();
