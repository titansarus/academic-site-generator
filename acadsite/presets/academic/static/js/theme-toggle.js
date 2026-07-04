// Light/dark theme toggle. The initial theme is set inline in <head> to avoid
// a flash; this script only wires up the toggle button and label.
(function () {
  var root = document.documentElement;
  var KEY = 'acadsite-theme';

  function current() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function syncLabels() {
    var isDark = current() === 'dark';
    document.querySelectorAll('[data-theme-label]').forEach(function (el) {
      el.textContent = isDark ? 'Dark' : 'Light';
    });
    document.querySelectorAll('[data-theme-toggle]').forEach(function (el) {
      el.setAttribute('aria-pressed', String(isDark));
    });
  }

  function toggle() {
    var next = current() === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    syncLabels();
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (btn) { e.preventDefault(); toggle(); }
  });

  syncLabels();
})();
