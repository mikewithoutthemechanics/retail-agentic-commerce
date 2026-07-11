"use client";

import { useState } from "react";
import { Navbar, PanelDivider } from "@/components/layout";
import { AgentPanel } from "@/components/agent";
import { BusinessPanel } from "@/components/business";
import { AgentActivityPanel } from "@/components/agent-activity";
import { WebhookToAgentActivityBridge } from "@/components/WebhookToAgentActivityBridge";
import { ACPLogProvider } from "@/hooks/useACPLog";
import { AgentActivityLogProvider } from "@/hooks/useAgentActivityLog";
import { Nebula } from "@/kui-foundations-react-external/nebula";
import type { CheckoutProtocol } from "@/types";

/**
 * Main page - Three-panel layout with Agent simulator, Merchant view, and Agent Activity
 * Uses CSS custom properties for consistent spacing (see globals.css)
 * Wrapped in ACPLogProvider and AgentActivityLogProvider to share logs between panels
 * Features NVIDIA-style Nebula animated background with gradient overlays
 */
export default function Home() {
  const [protocol, setProtocol] = useState<CheckoutProtocol>("acp");

  return (
    <ACPLogProvider>
      <AgentActivityLogProvider>
        <WebhookToAgentActivityBridge />
        <div className="min-h-screen h-screen bg-surface-base relative overflow-hidden">
          {/* Nebula Background */}
          <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
            <div className="w-full h-full">
              <Nebula variant="ambient" />
            </div>
          </div>

          {/* Top Green Gradient Overlay */}
          <div className="pointer-events-none gradient-overlay-top" />

          {/* Bottom Green Gradient Overlay */}
          <div className="pointer-events-none gradient-overlay-bottom" />

          {/* Content Layer */}
          <div className="relative flex flex-col h-full z-[1]">
            <Navbar />
            {/* Outer container with generous gutters for premium feel */}
            <div className="flex-1 flex flex-col min-h-0 p-6 px-10">
              <main className="flex-1 flex items-stretch w-full h-full min-h-0 gap-8">
                {/* Agent Panel Container */}
                <div className="flex-1 flex min-w-0">
                  <AgentPanel protocol={protocol} />
                </div>

                <PanelDivider />

                {/* Merchant Panel Container */}
                <div className="flex-1 flex min-w-0">
                  <BusinessPanel protocol={protocol} onProtocolChange={setProtocol} />
                </div>

                {/* Agent Activity Panel Container - no divider, same visual group as Merchant */}
                <div className="flex-1 flex min-w-0">
                  <AgentActivityPanel />
                </div>
              </main>
            </div>
          </div>
        </div>
      </AgentActivityLogProvider>
    </ACPLogProvider>
  );
}
