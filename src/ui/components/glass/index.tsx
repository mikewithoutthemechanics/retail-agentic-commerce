"use client";

import { cn } from "@/lib/utils";

/**
 * Glassmorphic primitives mapped to the shared design tokens defined in
 * `app/globals.css`. These are KUI-compatible: they accept a `className`
 * (merged with `cn`), forward standard HTML attributes, and compose over
 * the existing `.glass-*` CSS classes so the glassmorphic design system
 * stays the single source of truth.
 */

type GlassVariant = "default" | "green" | "yellow" | "gray";

/* ----------------------------------------------------------------
   GlassPanel
   ---------------------------------------------------------------- */
export interface GlassPanelProps extends React.HTMLAttributes<HTMLElement> {
  as?: "section" | "div";
}

export function GlassPanel({
  as: Tag = "section",
  className,
  children,
  ...props
}: GlassPanelProps) {
  return (
    <Tag className={cn("glass-panel", className)} {...props}>
      {children}
    </Tag>
  );
}

/* ----------------------------------------------------------------
   GlassDot
   ---------------------------------------------------------------- */
export interface GlassDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  live?: boolean;
}

export function GlassDot({ live = false, className, ...props }: GlassDotProps) {
  return <span className={cn("glass-dot", live && "live", className)} {...props} />;
}

/* ----------------------------------------------------------------
   GlassBadge
   ---------------------------------------------------------------- */
export interface GlassBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: GlassVariant;
}

export function GlassBadge({
  variant = "default",
  className,
  children,
  ...props
}: GlassBadgeProps) {
  return (
    <span className={cn("glass-badge", variant !== "default" && variant, className)} {...props}>
      {children}
    </span>
  );
}

/* ----------------------------------------------------------------
   GlassTag
   ---------------------------------------------------------------- */
export interface GlassTagProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: Exclude<GlassVariant, "gray">;
}

export function GlassTag({ variant = "default", className, children, ...props }: GlassTagProps) {
  return (
    <span className={cn("glass-tag", variant !== "default" && variant, className)} {...props}>
      {children}
    </span>
  );
}
