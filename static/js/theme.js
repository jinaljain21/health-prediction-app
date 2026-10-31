// Light / dark mode. Loaded in <head> so the saved theme is applied before the page is drawn.
(function () {
  const STORAGE_KEY = "theme";
  const root = document.documentElement;

  function savedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function applyTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
    const icon = document.querySelector("#theme-toggle i");
    if (icon) icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
  }

  // First visit: follow the computer's own light/dark setting
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  applyTheme(savedTheme() || systemTheme);

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(root.getAttribute("data-bs-theme"));
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", () => {
      const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Private browsing can block storage; the toggle still works for this page
      }
    });
  });

  // Always print on a white page, then switch back
  let themeBeforePrint = null;
  window.addEventListener("beforeprint", () => {
    themeBeforePrint = root.getAttribute("data-bs-theme");
    applyTheme("light");
  });
  window.addEventListener("afterprint", () => {
    if (themeBeforePrint) applyTheme(themeBeforePrint);
  });
})();
