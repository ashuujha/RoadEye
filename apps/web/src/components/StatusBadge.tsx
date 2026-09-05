import React from "react";
import { IconCheckCircle, IconAlertTriangle, IconXCircle, IconClock } from "./Icons";

export type StatusKind =
  | "accepted"
  | "observed"
  | "fresh"
  | "done"
  | "plausible"
  | "approved"
  | "valid"
  | "review_required"
  | "ambiguous"
  | "stale"
  | "leased"
  | "uncertain"
  | "rejected"
  | "poison"
  | "error"
  | "failed"
  | "revoked"
  | "incorrect"
  | "duplicate"
  | "pending"
  | "draft"
  | "inferred"
  | "playing"
  | "paused"
  | string;

interface StatusBadgeProps {
  status: StatusKind | null | undefined;
  label?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, label, size = "md" }: StatusBadgeProps) {
  if (!status) return <span className="status-badge status-empty">Unknown</span>;

  const s = String(status).toLowerCase();
  let category: "success" | "warning" | "danger" | "info" | "neutral" = "neutral";
  let icon = <IconClock size={size === "sm" ? 12 : 14} />;

  if (["accepted", "observed", "fresh", "done", "plausible", "approved", "valid", "correct"].includes(s)) {
    category = "success";
    icon = <IconCheckCircle size={size === "sm" ? 12 : 14} />;
  } else if (["review_required", "ambiguous", "stale", "leased", "uncertain", "partial"].includes(s)) {
    category = "warning";
    icon = <IconAlertTriangle size={size === "sm" ? 12 : 14} />;
  } else if (["rejected", "poison", "error", "failed", "revoked", "incorrect", "missing"].includes(s)) {
    category = "danger";
    icon = <IconXCircle size={size === "sm" ? 12 : 14} />;
  } else if (["inferred", "playing"].includes(s)) {
    category = "info";
  }

  const displayText = label || s.replace(/_/g, " ");

  return (
    <span className={`status-badge status-${category} status-${size}`} title={s}>
      {icon}
      <span>{displayText}</span>
    </span>
  );
}
