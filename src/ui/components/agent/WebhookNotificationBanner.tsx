"use client";

interface WebhookNotificationBannerProps {
  notification: {
    subject: string;
    message: string;
    status: string;
    orderId: string;
  };
  onDismiss: () => void;
}

export function WebhookNotificationBanner({
  notification,
  onDismiss,
}: WebhookNotificationBannerProps) {
  return (
    <div className="flex items-start gap-3 m-6 mb-4 p-4 rounded-xl border border-[rgba(118,185,0,0.25)] bg-gradient-to-br from-[rgba(118,185,0,0.12)] to-[rgba(118,185,0,0.06)] animate-[slideDown_300ms_ease-out]">
      <div className="shrink-0 w-5 h-5 text-[#76b900] mt-[2px]">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="w-full h-full"
        >
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-semibold text-[#76b900] mb-1 leading-tight">
          {notification.subject}
        </div>
        <div className="text-xs text-white/80 leading-relaxed whitespace-pre-wrap mb-1.5">
          {notification.message}
        </div>
        <div className="text-[10px] text-white/45 capitalize">
          Order: {notification.orderId.slice(0, 12)}... • {notification.status.replace(/_/g, " ")}
        </div>
      </div>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="shrink-0 w-[18px] h-[18px] p-0 border-none bg-transparent text-white/40 cursor-pointer transition-colors duration-200 hover:text-white/80"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="w-full h-full"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>

      <style jsx>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
