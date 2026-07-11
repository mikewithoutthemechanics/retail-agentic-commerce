import { GlassDot } from "./GlassDot";

interface GlassBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "green" | "yellow" | "gray";
  live?: boolean;
}

export function GlassBadge({
  variant = "gray",
  live,
  className = "",
  children,
  ...props
}: GlassBadgeProps) {
  return (
    <div className={`glass-badge ${variant} ${className}`} {...props}>
      {live !== false && <GlassDot />}
      {children}
    </div>
  );
}
