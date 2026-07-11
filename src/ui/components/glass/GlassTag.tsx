interface GlassTagProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "green" | "yellow";
}

export function GlassTag({
  variant = "default",
  className = "",
  children,
  ...props
}: GlassTagProps) {
  return (
    <div className={`glass-tag ${variant} ${className}`} {...props}>
      {children}
    </div>
  );
}
