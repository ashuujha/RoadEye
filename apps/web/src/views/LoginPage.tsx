import React, { useState } from "react";
import { IconShield } from "../components/Icons";
import type { components } from "../api.generated";

interface LoginPageProps {
  onLogin: (actor: components["schemas"]["Role"], password: string) => Promise<void>;
  onExploreOffline: () => void;
  onBackToDashboard?: () => void;
  busy: boolean;
  message: string;
  backendReady?: boolean;
}

export function LoginPage({
  onLogin,
  onExploreOffline,
  onBackToDashboard,
  busy,
  message,
  backendReady,
}: LoginPageProps) {
  const [operatorId, setOperatorId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState<components["schemas"]["Role"]>("administrator");

  const handleOperatorIdChange = (val: string) => {
    setOperatorId(val);
    const lower = val.toLowerCase().trim();
    if (lower.includes("investigat")) setSelectedRole("investigator");
    else if (lower.includes("view")) setSelectedRole("viewer");
    else if (lower.includes("approv")) setSelectedRole("approver");
    else if (lower.includes("admin")) setSelectedRole("administrator");
  };

  const handleRoleSelect = (role: components["schemas"]["Role"]) => {
    setSelectedRole(role);
    setOperatorId(role);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onLogin(selectedRole, password);
  };

  return (
    <div className="login-cinema-root pixel-login-root">
      {/* 1. CINEMATIC PIXEL-ART STAGE (Handcrafted 16-bit retro-futuristic traffic surveillance) */}
      <div className="cinema-stage pixel-art-stage" aria-hidden="true">
        {/* Video stage */}
        <div className="stage-matte pixel-stage-matte">
          <video
            autoPlay
            loop
            muted
            playsInline
            className="stage-bg-image pixel-bg-image"
          >
            <source src="/login-bg.mp4" type="video/mp4" />
          </video>
        </div>

        {/* Ambient sunset atmospheric lighting */}
        <div className="ambient-sunset-glow" />
      </div>

      {/* 2. RIGHT-SIDE PREMIUM PIXEL-ART OPERATIONS LOGIN CARD */}
      <main className="login-card-wrapper pixel-card-wrapper" role="main">
        <div className="glass-login-card pixel-login-card">
          {/* Card Header matching authority operations standard */}
          <div className="card-header pixel-card-header">
            {onBackToDashboard && (
              <button
                type="button"
                className="pixel-back-link-btn"
                onClick={onBackToDashboard}
                title="Return to Dashboard Preview"
              >
                ← Back to Overview
              </button>
            )}
            <h1 className="welcome-title pixel-title">Operator Access</h1>
            <p className="welcome-subtitle pixel-subtitle">
              Restricted Authority Console · SIH 26127 · Bharat Electronics Limited
            </p>
          </div>

          {/* Offline / Local Evaluation Mode State Banner */}
          {!backendReady && (
            <div className="login-offline-banner" role="status">
              <div className="offline-banner-icon">
                <IconShield size={16} />
              </div>
              <div className="offline-banner-text">
                <strong>LOCAL EVALUATION MODE</strong>
                <span>FastAPI backend (:8000) is disconnected. Enter local evaluation to inspect schematics and sample records.</span>
              </div>
              <button
                type="button"
                className="btn-offline-entry"
                onClick={onExploreOffline}
              >
                Explore Evaluation Console →
              </button>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="glass-form pixel-form" noValidate>
            {/* Operator ID Field */}
            <div className="form-field pixel-field">
              <label htmlFor="operator-id-input" className="form-label">OPERATOR ID</label>
              <input
                id="operator-id-input"
                type="text"
                value={operatorId}
                onChange={(e) => handleOperatorIdChange(e.target.value)}
                placeholder="e.g. administrator or officer@gov.in"
                className="glass-input pixel-input"
                autoComplete="username"
                aria-label="Operator ID"
                required
              />
            </div>

            {/* Quick Role Selection Chips */}
            <div className="role-preset-row" aria-label="Select default role preset">
              <span className="preset-label">Preset:</span>
              <button
                type="button"
                className={`preset-chip ${selectedRole === "administrator" ? "active" : ""}`}
                onClick={() => handleRoleSelect("administrator")}
              >
                Admin
              </button>
              <button
                type="button"
                className={`preset-chip ${selectedRole === "investigator" ? "active" : ""}`}
                onClick={() => handleRoleSelect("investigator")}
              >
                Investigator
              </button>
              <button
                type="button"
                className={`preset-chip ${selectedRole === "approver" ? "active" : ""}`}
                onClick={() => handleRoleSelect("approver")}
              >
                Approver
              </button>
              <button
                type="button"
                className={`preset-chip ${selectedRole === "viewer" ? "active" : ""}`}
                onClick={() => handleRoleSelect("viewer")}
              >
                Viewer
              </button>
            </div>

            {/* Access Credential Field */}
            <div className="form-field pixel-field">
              <label htmlFor="access-credential-input" className="form-label">ACCESS CREDENTIAL</label>
              <input
                id="access-credential-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password or credential token"
                className="glass-input pixel-input"
                autoComplete="current-password"
                aria-label="Access Credential"
              />
            </div>

            {/* Error or Feedback Alert */}
            {message && (
              <div
                className="login-alert alert-error"
                role="status"
              >
                {message}
              </div>
            )}

            {/* Primary Login Button */}
            <button
              type="submit"
              className="btn-login-primary pixel-btn-primary"
              disabled={busy}
            >
              <span>{busy ? "Authenticating…" : "Authenticate & Enter →"}</span>
            </button>

            {/* Direct Evaluation Option */}
            <div className="login-footer-row">
              <button
                type="button"
                className="login-bypass-link"
                onClick={onExploreOffline}
              >
                Or enter local evaluation mode without credentials
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
