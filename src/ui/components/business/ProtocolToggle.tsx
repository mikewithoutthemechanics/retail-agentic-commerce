"use client";

import type { CheckoutProtocol } from "@/types";

interface ProtocolToggleProps {
  protocol: CheckoutProtocol;
  onProtocolChange: (protocol: CheckoutProtocol) => void;
}

export function ProtocolToggle({ protocol, onProtocolChange }: ProtocolToggleProps) {
  return (
    <div
      className="inline-flex gap-1 p-1 rounded-[10px] border border-glass-border-subtle bg-block-bg"
      role="tablist"
      aria-label="Protocol selector"
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
            className={`
              min-w-[52px] px-3 py-[6px] rounded-[8px] border-none cursor-pointer
              text-xs font-semibold tracking-wider
              transition-all duration-200 ease-out
              ${active ? "text-accent-green bg-accent-green-bg" : "text-text-muted bg-transparent"}
            `}
          >
            {tab.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
