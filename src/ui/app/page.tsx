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
        <div className="bg-surface-base relative h-screen min-h-screen overflow-hidden">
          {/* Nebula Background */}
          <div
            aria-hidden="true"
            className="pointer-events-none fixed inset-0 z-0 h-screen w-screen overflow-hidden"
          >
            <div className="h-full w-full">
              <Nebula variant="ambient" />
            </div>
          </div>

          {/* Top Green Gradient Overlay (KUI green-100 -> blue-200) */}
          <div
            aria-hidden="true"
            className="pointer-events-none fixed left-0 right-0 top-0 z-0 h-[500px] opacity-[0.12]
              bg-[linear-gradient(80.22deg,var(--color-green-100)_1.49%,var(--color-blue-200)_99.95%)]
              [mask-image:radial-gradient(ellipse_150%_120%_at_top,black_0%,black_30%,transparent_70%)]
              [-webkit-mask-image:radial-gradient(ellipse_150%_120%_at_top,black_0%,black_30%,transparent_70%)]"
          />

          {/* Bottom Green Gradient Overlay (KUI green-100 -> blue-200) */}
          <div
            aria-hidden="true"
            className="pointer-events-none fixed bottom-0 left-0 right-0 z-0 h-[300px] opacity-[0.12]
              bg-[linear-gradient(80.22deg,var(--color-green-100)_1.49%,var(--color-blue-200)_99.95%)]
              [mask-image:radial-gradient(ellipse_120%_130%_at_bottom,black_0%,black_25%,transparent_60%)]
              [-webkit-mask-image:radial-gradient(ellipse_120%_130%_at_bottom,black_0%,black_25%,transparent_60%)]"
          />

          {/* Content Layer */}
          <div className="relative z-[1] flex h-full flex-col">
            <Navbar />
            {/* Outer container with generous gutters for premium feel */}
            <div className="flex min-h-0 flex-1 flex-col px-10 py-6">
              <main className="flex h-full w-full min-h-0 items-stretch gap-8">
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
