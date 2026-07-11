import { cn } from "@/lib/utils";

interface GlassIconBoxProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "w-8 h-8 rounded-lg",
  md: "w-12 h-12 rounded-[14px]",
  lg: "w-16 h-16 rounded-[18px]",
};

export function GlassIconBox({
  size = "md",
  className = "",
  children,
  ...props
}: GlassIconBoxProps) {
  return (
    <div
      className={cn(
        "bg-block-bg border border-glass-border flex items-center justify-center",
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
