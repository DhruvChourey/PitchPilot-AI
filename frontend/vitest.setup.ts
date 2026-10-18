// jsdom doesn't implement matchMedia. Several existing components (e.g.
// Reveal, via lib/motion's prefersReducedMotion()) call it unconditionally
// -- this stub lets those components render in tests without pretending
// they're reduced-motion-specific behavior under test.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
