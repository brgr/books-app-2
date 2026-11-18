/**
 * Whether this is an ordinary left click, which we may handle ourselves.
 *
 * Clicks with a modifier key or another button belong to the browser, e.g. Ctrl/Cmd-click to open a link in a new tab.
 */
export function isPlainLeftClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

/**
 * Swallows the click that finishes the current press, so a press that dismissed something (like a menu's backdrop)
 * doesn't also activate whatever was underneath it.
 *
 * How long that click takes varies (iOS may hold it back to watch for a double-tap), and some browsers send none at all
 * once the pressed element is gone. So rather than after a fixed time, this stops at the next press.
 */
export function swallowNextClick() {
  const swallow = (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    stop();
  };

  const stop = () => {
    clearTimeout(timer);
    document.removeEventListener("click", swallow, true);
    document.removeEventListener("pointerdown", stop, true);
  };

  // Only a safety net, for a click that is neither sent nor followed by another press, e.g. a keyboard's
  const timer = setTimeout(stop, 1500);
  
  document.addEventListener("click", swallow, true);
  // Added while the current press is past its capture phase, so only the next one ends this
  document.addEventListener("pointerdown", stop, true);
}
