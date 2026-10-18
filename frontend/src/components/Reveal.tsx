"use client";

import { useRef, type ReactNode } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { DURATION, EASE, STAGGER, prefersReducedMotion } from "@/lib/motion";

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** Stagger direct children in on mount, instead of animating the
   * container as a single block. Use for a row of cards/sections or a
   * list of rows. */
  stagger?: boolean;
  delay?: number;
  /** Remount key -- pass something that changes (e.g. page+filter) to
   * re-trigger the entrance animation for genuinely new content, such as
   * a list refreshing after a filter change. */
  animKey?: string | number;
}

/** Thin, reusable GSAP entrance wrapper: fade + slight rise, cleaned up
 * automatically via useGSAP's scope (reverts on unmount/dependency change,
 * so no manual gsap.context()/ctx.revert() bookkeeping per component). */
export default function Reveal({ children, className, stagger = false, delay = 0, animKey }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (!ref.current) return;
      const targets = stagger ? Array.from(ref.current.children) : ref.current;

      if (prefersReducedMotion()) {
        gsap.set(targets, { opacity: 1, y: 0 });
        return;
      }

      gsap.fromTo(
        targets,
        { opacity: 0, y: 14 },
        {
          opacity: 1,
          y: 0,
          duration: DURATION,
          ease: EASE,
          delay,
          stagger: stagger ? STAGGER : 0,
        }
      );
    },
    { scope: ref, dependencies: [animKey] }
  );

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
