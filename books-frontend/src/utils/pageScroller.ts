/** The element the current page scrolls in (see App.vue); the window itself never scrolls */
export function pageScroller(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".page-scroller");
}
