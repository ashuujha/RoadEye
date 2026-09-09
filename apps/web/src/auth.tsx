import { useState, type FormEvent, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  RoadEyeApiError,
  actors,
  api,
  type Actor,
  type AuthSession,
} from "./api";

export type AuthenticationState =
  | { readonly status: "loading" }
  | { readonly status: "anonymous" }
  | { readonly status: "authenticated"; readonly session: AuthSession }
  | { readonly status: "error"; readonly message: string };

export type AuthenticationEvent =
  | { readonly type: "DISCOVERY_STARTED" }
  | { readonly type: "SESSION_FOUND"; readonly session: AuthSession }
  | { readonly type: "SESSION_MISSING" }
  | { readonly type: "DISCOVERY_FAILED"; readonly message: string }
  | { readonly type: "SIGNED_OUT" }
  | { readonly type: "SESSION_EXPIRED" };

export const initialAuthenticationState: AuthenticationState = {
  status: "loading",
};

export function authenticationReducer(
  _state: AuthenticationState,
  event: AuthenticationEvent,
): AuthenticationState {
  switch (event.type) {
    case "DISCOVERY_STARTED":
      return { status: "loading" };
    case "SESSION_FOUND":
      return { status: "authenticated", session: event.session };
    case "SESSION_MISSING":
    case "SIGNED_OUT":
    case "SESSION_EXPIRED":
      return { status: "anonymous" };
    case "DISCOVERY_FAILED":
      return { status: "error", message: event.message };
  }
}

export function loginErrorMessage(error: unknown): string {
  if (
    error instanceof RoadEyeApiError &&
    error.status === 401 &&
    error.detail === "INVALID_CREDENTIALS"
  ) {
    return "Invalid actor or password.";
  }
  return error instanceof Error
    ? error.message
    : "Sign in failed. Check that the local service is running.";
}

function LoginBackdrop({ children }: { readonly children: ReactNode }) {
  return (
    <div className="operator-login-page">
      <section
        className="operator-login-visual"
        aria-label="RoadEye city monitoring"
      >
        <div className="operator-login-visual-copy">
          <p className="operator-city-badge">
            <span aria-hidden="true">▣</span>
            Built for real-moving cities
          </p>
          <h1>Find Signal to Action Instantly</h1>
          <p className="operator-city-line">
            CITIES SAFER <i /> ROADS SMARTER <i /> INDIA STRONGER
          </p>
        </div>
      </section>
      <section className="operator-login-access">{children}</section>
    </div>
  );
}

interface LoginPageProps {
  readonly onAuthenticated: (session: AuthSession) => void;
  readonly discoveryError?: string;
  readonly onRetryDiscovery?: () => void;
  readonly onBackToLanding?: () => void;
}

export function LoginPage({
  onAuthenticated,
  discoveryError,
  onRetryDiscovery,
  onBackToLanding,
}: LoginPageProps) {
  const [actor, setActor] = useState<Actor>("administrator");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.health({ signal }),
    staleTime: 30_000,
  });

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const session = await api.login({ actor, password });
      setPassword("");
      onAuthenticated(session);
    } catch (error) {
      setMessage(loginErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <LoginBackdrop>
      <main className="operator-login-card">
        <button
          className="operator-back-link"
          type="button"
          onClick={onBackToLanding}
          disabled={!onBackToLanding}
        >
          ← Back to Overview
        </button>
        <h1>Operator Access</h1>
        <p className="operator-login-subtitle">
          Restricted local console · authenticated read-only evidence
        </p>

        <div className="operator-evaluation-box">
          <strong>LOCAL EVALUATION MODE</strong>
          <p>
            Review audited predictions and source records through the local,
            session-protected service.
          </p>
          <span>Evidence console ready →</span>
        </div>

        <form onSubmit={signIn}>
          <label className="operator-field">
            Operator ID
            <input type="text" value={actor} readOnly aria-label="Operator ID" />
          </label>

          <div className="operator-presets" aria-label="Actor presets">
            <span>PRESET:</span>
            {actors.map((value) => (
              <button
                key={value}
                type="button"
                className={actor === value ? "selected" : ""}
                aria-pressed={actor === value}
                onClick={() => setActor(value)}
              >
                {value === "administrator" ? "Admin" : value}
              </button>
            ))}
          </div>

          <label className="operator-field">
            Access Credential
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="Enter password or credential token"
              required
            />
          </label>

          <button
            className="operator-authenticate"
            type="submit"
            disabled={busy}
          >
            {busy ? "Authenticating…" : "Authenticate & Enter →"}
          </button>
        </form>

        {(message || discoveryError) && (
          <p className="operator-alert" role="alert">
            {message || discoveryError}
          </p>
        )}
        {discoveryError && onRetryDiscovery && (
          <button
            type="button"
            className="operator-retry"
            onClick={onRetryDiscovery}
          >
            Retry session check
          </button>
        )}
        <p className="operator-login-footnote">
          Local credentials are required · sessions expire after eight hours
        </p>
        <p className="operator-login-health" aria-live="polite">
          <span className={health.data ? "health-ready" : "health-pending"} />
          {health.data
            ? "Local service ready"
            : health.isError
              ? "Local service unavailable"
              : "Checking local service…"}
        </p>
      </main>
    </LoginBackdrop>
  );
}

interface SessionGateProps {
  readonly state: AuthenticationState;
  readonly onAuthenticated: (session: AuthSession) => void;
  readonly onRetryDiscovery: () => void;
  readonly onBackToLanding?: () => void;
  readonly children: ReactNode;
}

export function SessionGate({
  state,
  onAuthenticated,
  onRetryDiscovery,
  onBackToLanding,
  children,
}: SessionGateProps) {
  if (state.status === "authenticated") return <>{children}</>;

  if (state.status === "loading") {
    return (
      <LoginBackdrop>
        <main
          className="operator-login-card login-session-loading"
          aria-live="polite"
        >
          <span className="session-spinner" aria-hidden="true" />
          <div>
            <p className="operator-loading-eyebrow">LOCAL ACCESS</p>
            <h1>Restoring your session</h1>
            <p>Checking the secure local session before loading evidence.</p>
          </div>
        </main>
      </LoginBackdrop>
    );
  }

  return (
    <LoginPage
      onAuthenticated={onAuthenticated}
      discoveryError={state.status === "error" ? state.message : undefined}
      onRetryDiscovery={state.status === "error" ? onRetryDiscovery : undefined}
      onBackToLanding={onBackToLanding}
    />
  );
}
