// Deferred scripts run in document order, after the page has been parsed.
(() => {
  const content = document.querySelector("main");
  if (!content || typeof window.renderMathInElement !== "function") return;

  window.renderMathInElement(content, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
    ],
    // Keep malformed expressions readable without interrupting other equations.
    throwOnError: false,
    trust: false,
    output: "htmlAndMathml",
  });

  // Long display equations scroll independently instead of widening the page.
  content.querySelectorAll(".katex-display").forEach((equation) => {
    equation.tabIndex = 0;
    equation.setAttribute("role", "group");
    equation.setAttribute("aria-label", "Display equation");
  });
})();
