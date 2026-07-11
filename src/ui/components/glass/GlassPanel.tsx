export function GlassPanel({
  className = "",
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`glass-panel ${className}`} {...props}>
      {children}
    </div>
  );
}
