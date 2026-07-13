"use client";

import { useEffect, useRef, useCallback } from "react";
import { useACPLog, type ACPEvent, type ACPEventType } from "@/hooks/useACPLog";
import { useCheckoutEvents } from "@/hooks/useCheckoutEvents";
import { GlassBadge, GlassDot, GlassPanel, GlassTag } from "@/components/glass";
import type { CheckoutProtocol } from "@/types";

/**
 * MCP Server base URL - uses nginx proxy in Docker, direct in development
 */
const MCP_SERVER_URL = process.env.NEXT_PUBLIC_MCP_SERVER_URL || "http://localhost:2091";

/**
 * Get display info for event types
 */
function getEventTypeInfo(type: ACPEventType): {
  label: string;
  variant: "default" | "green" | "yellow";
  icon: string;
} {
  switch (type) {
    case "session_create":
      return { label: "CREATE", variant: "green", icon: "+" };
    case "session_update":
      return { label: "UPDATE", variant: "default", icon: "↻" };
    case "delegate_payment":
      return { label: "DELEGATE", variant: "yellow", icon: "🔐" };
    case "session_complete":
      return { label: "COMPLETE", variant: "green", icon: "✓" };
    case "webhook_post":
      return { label: "WEBHOOK", variant: "green", icon: "📤" };
  }
}

/**
 * Format timestamp to readable time
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Single ACP Event Item in the timeline (glass style)
 */
function ACPEventItem({ event }: { event: ACPEvent }) {
  const typeInfo = getEventTypeInfo(event.type);
  const isPending = event.status === "pending";
  const isError = event.status === "error";

  return (
    <div className="glass-event">
      <div className="time">{formatTime(event.timestamp)}</div>
      <div className="msg">
        {isPending ? (
          <span className="text-glass-fg-muted">Processing request...</span>
        ) : (
          <>
            <div className="overflow-hidden text-ellipsis whitespace-nowrap">
              <span className="text-glass-fg-muted">{event.method}</span>{" "}
              <span className="text-glass-fg-secondary">{event.endpoint}</span>
            </div>
            {event.responseSummary && (
              <span className={`block mt-1 ${isError ? "text-[#FF6B6B]" : "text-accent-green"}`}>
                {isError ? "✗" : "✓"} {event.responseSummary}
              </span>
            )}
            {event.duration != null && event.duration > 0 && (
              <span className="block mt-0.5 text-glass-fg-faint text-[11px]">
                {event.duration}ms
              </span>
            )}
          </>
        )}
      </div>
      <GlassTag variant={isError ? "default" : typeInfo.variant}>
        {isPending ? "PENDING" : isError ? "ERROR" : typeInfo.label}
      </GlassTag>
    </div>
  );
}

/**
 * Empty state with waiting message
 */
function EmptyState({ protocol }: { protocol: CheckoutProtocol }) {
  const protocolLabel = protocol === "ucp" ? "UCP" : "ACP";

  return (
    <div className="glass-content flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      {/* Icon */}
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-[14px] border border-glass-border bg-block-bg">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-glass-fg-muted"
        >
          <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      </div>
      <h3 className="mb-2 text-[14px] font-semibold text-glass-fg-secondary">No active session</h3>
      <p className="m-0 max-w-[240px] text-[12px] leading-[1.45] text-glass-fg-muted">
        Select a product from the Client Agent panel to start a checkout session using{" "}
        {protocolLabel}.
      </p>
    </div>
  );
}

/**
 * Active session view with event timeline (glass style)
 */
function ActiveSession({
  events,
  onClear,
  protocol,
}: {
  events: ACPEvent[];
  onClear: () => void;
  protocol: CheckoutProtocol;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new events arrive (newest first)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  const protocolLabel = protocol === "ucp" ? "UCP" : "ACP";

  return (
    <div className="glass-content flex flex-col gap-3.5">
      {/* Header with request count */}
      <div className="mb-2 flex items-center justify-between">
        <h3 className="m-0 text-[12px] uppercase tracking-[0.8px] text-glass-fg-secondary">
          {protocolLabel} Communication
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[12px] text-glass-fg-muted">
            {events.length} request{events.length !== 1 ? "s" : ""}
          </span>
          <button
            onClick={onClear}
            title="Clear all logs"
            className="cursor-pointer rounded-[6px] border border-glass-border bg-block-bg px-2.5 py-1 text-[11px] font-medium text-glass-fg-muted transition-colors hover:bg-glass-border hover:text-glass-fg-secondary"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div ref={scrollRef} className="glass-timeline max-h-[calc(100vh-200px)] overflow-y-auto">
        {[...events].reverse().map((event) => (
          <ACPEventItem key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}

function ProtocolToggle({
  protocol,
  onProtocolChange,
}: {
  protocol: CheckoutProtocol;
  onProtocolChange: (protocol: CheckoutProtocol) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Protocol selector"
      className="inline-flex gap-1 rounded-[10px] border border-glass-border-subtle bg-block-bg p-1"
    >
      {(["acp", "ucp"] as const).map((tab) => {
        const active = protocol === tab;
        return (
          <button
            key={tab}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onProtocolChange(tab)}
            className={`min-w-[52px] cursor-pointer rounded-lg border-0 px-3 py-1.5 text-[12px] font-semibold tracking-[0.4px] transition-all duration-200 ${
              active ? "bg-accent-green-bg text-accent-green" : "text-glass-fg-muted"
            }`}
          >
            {tab.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Right panel showing merchant/retailer view with ACP communication log
 * Uses glassmorphic design system
 */
interface BusinessPanelProps {
  protocol: CheckoutProtocol;
  onProtocolChange: (protocol: CheckoutProtocol) => void;
}

export function BusinessPanel({ protocol, onProtocolChange }: BusinessPanelProps) {
  const { state, clear } = useACPLog();
  const hasEvents = state.events.length > 0;

  // Subscribe to SSE checkout events from MCP server
  // This allows the widget to remain isolated (no postMessage)
  useCheckoutEvents();

  // Clear local ACP log state and server-side event store
  // Note: Agent Activity is cleared by switching tabs or refreshing the page
  const handleClear = useCallback(async () => {
    // Clear local state first for immediate UI feedback
    clear();

    // Also clear server-side event store (fire and forget, ignore errors)
    try {
      await fetch(`${MCP_SERVER_URL}/events`, { method: "DELETE" });
    } catch {
      // Silently ignore - server may not be running
    }
  }, [clear]);

  const handleProtocolChange = useCallback(
    (nextProtocol: CheckoutProtocol) => {
      if (nextProtocol === protocol) {
        return;
      }
      clear();
      onProtocolChange(nextProtocol);
    },
    [clear, onProtocolChange, protocol]
  );

  return (
    <GlassPanel className="flex flex-1 flex-col h-full overflow-hidden" aria-label="Merchant Panel">
      {/* Glass Panel Header */}
      <div className="glass-panel-header">
        <div className="flex items-center justify-between gap-3">
          <GlassBadge variant={hasEvents ? "yellow" : "gray"}>
            <GlassDot live={hasEvents} />
            Merchant Server
          </GlassBadge>
          <ProtocolToggle protocol={protocol} onProtocolChange={handleProtocolChange} />
        </div>
      </div>

      {/* Content - either empty state or active session */}
      {state.events.length === 0 ? (
        <EmptyState protocol={protocol} />
      ) : (
        <ActiveSession events={state.events} onClear={handleClear} protocol={protocol} />
      )}
    </GlassPanel>
  );
}
