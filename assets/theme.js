(() => {
  const storageKey = 'caio-color-theme';
  const themeColor = { light: '#ffffff', dark: '#121317' };

  const storedTheme = () => {
    try {
      const value = localStorage.getItem(storageKey);
      return value === 'light' || value === 'dark' ? value : null;
    } catch {
      return null;
    }
  };

  const preferredTheme = () => storedTheme() || 'dark';

  const applyTheme = (theme) => {
    const previousTheme = document.documentElement.dataset.theme;
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = themeColor[theme];

    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
      const dark = theme === 'dark';
      toggle.setAttribute('aria-pressed', String(dark));
      toggle.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} mode`);
      toggle.title = `Switch to ${dark ? 'light' : 'dark'} mode`;
    }

    if (previousTheme && previousTheme !== theme) {
      window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }
  };

  applyTheme(preferredTheme());

  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(preferredTheme());
    const toggle = document.querySelector('.theme-toggle');
    toggle?.addEventListener('click', () => {
      const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(storageKey, theme);
      } catch {
        // The selected theme still applies for this page when storage is unavailable.
      }
      applyTheme(theme);
    });
  });
})();
