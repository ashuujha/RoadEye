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
    <div className="login-page-wrapper">
      <video
        className="login-bg-video"
        autoPlay
        loop
        muted
        playsInline
        poster="/roadeye-login-bg.png"
        aria-hidden="true"
        tabIndex={-1}
      >
        <source src="/login-bg.mp4" type="video/mp4" />
      </video>
      <div className="login-bg-overlay" aria-hidden="true" />
      {children}
    </div>
  );
}

interface LoginPageProps {
  readonly onAuthenticated: (session: AuthSession) => void;
  readonly discoveryError?: string;
  readonly onRetryDiscovery?: () => void;
}

export function LoginPage({
  onAuthenticated,
  discoveryError,
  onRetryDiscovery,
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
      <header className="login-header">
        <div className="login-brand-copy">
          <strong>RoadEye</strong>
          <span>Evidence-first operations · local demo</span>
        </div>
        <span className="synthetic-banner-unauth">
          AUDITED PREDICTIONS · READ-ONLY
        </span>
      </header>

      <main className="login">
        <p className="login-eyebrow">LOCAL ACCESS</p>
        <h1>Local demonstration sign in</h1>
        <p>
          Inspect hash-verified prediction evidence. Every demo actor has identical
          read-only access.
        </p>

        <form onSubmit={signIn}>
          <label>
            Local actor
            <select
              value={actor}
              onChange={(event) => setActor(event.target.value as Actor)}
            >
              {actors.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label>
            Local password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {(message || discoveryError) && (
          <p role="alert">{message || discoveryError}</p>
        )}
        {discoveryError && onRetryDiscovery && (
          <button
            type="button"
            className="login-retry"
            onClick={onRetryDiscovery}
          >
            Retry session check
          </button>
        )}
        <p className="login-help">
          Use the password supplied through the server's ignored local environment.
          Sessions last up to eight hours and reset when the backend restarts.
        </p>
        <p className="login-health" aria-live="polite">
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
  readonly children: ReactNode;
}

export function SessionGate({
  state,
  onAuthenticated,
  onRetryDiscovery,
  children,
}: SessionGateProps) {
  if (state.status === "authenticated") return <>{children}</>;

  if (state.status === "loading") {
    return (
      <LoginBackdrop>
        <main className="login login-session-loading" aria-live="polite">
          <span className="session-spinner" aria-hidden="true" />
          <div>
            <p className="login-eyebrow">LOCAL ACCESS</p>
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
    />
  );
}
