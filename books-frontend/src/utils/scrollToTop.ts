import { pageScroller } from "./pageScroller";

export function scrollToTop() {
  pageScroller()?.scrollTo({
    top: 0,
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
  });
}
