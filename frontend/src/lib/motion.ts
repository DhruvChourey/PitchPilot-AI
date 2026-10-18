/** Shared GSAP timing/easing + prefers-reduced-motion helper, so every
 * animated component stays consistent and respects the user's OS setting. */

export const EASE = "power2.out";
export const EASE_SOFT = "power1.out";
export const DURATION_FAST = 0.22;
export const DURATION = 0.35;
export const DURATION_SLOW = 0.5;
export const STAGGER = 0.06;

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
