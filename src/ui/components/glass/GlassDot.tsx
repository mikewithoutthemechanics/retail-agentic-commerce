interface GlassDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  live?: boolean;
}

export function GlassDot({ live, className = "", ...props }: GlassDotProps) {
  return <span className={`glass-dot ${live ? "live" : ""} ${className}`} {...props} />;
}
