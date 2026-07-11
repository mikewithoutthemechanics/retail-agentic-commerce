type GlassButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export function GlassButton({ className = "", children, ...props }: GlassButtonProps) {
  return (
    <button className={`glass-btn ${className}`} {...props}>
      {children}
    </button>
  );
}
