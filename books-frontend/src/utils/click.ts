/**
 * Whether this is an ordinary left click, which we may handle ourselves.
 *
 * Clicks with a modifier key or another button belong to the browser, e.g. Ctrl/Cmd-click to open a link in a new tab.
 */
export function isPlainLeftClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}
